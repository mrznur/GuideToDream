"""
app/services/research_orchestrator.py
───────────────────────────────────────
Orchestrates a full research cycle end-to-end.

This is the heart of the agent. It coordinates all components:
profile loading → query generation → web search → page fetch →
extraction → eligibility → scoring → database persistence.

DESIGN PRINCIPLES:

1. Never crash the whole pipeline on one failure.
   If fetching one URL fails, log the error and continue to the next URL.
   The research run completes with partial results rather than failing entirely.

2. Every failure is logged to the research_runs.errors JSONB column.
   You can inspect exactly what went wrong after the fact.

3. Rate limiting and crawl delay are respected.
   We add a delay between requests to the same domain.

4. The pipeline is idempotent.
   Running it twice doesn't create duplicate programmes in the database.
   It updates existing records and detects changes.

5. All costs are tracked.
   Every LLM call logs token usage. The research run records total cost.

CONCURRENCY NOTE:
This runs sequentially (one URL at a time) for simplicity.
In a future milestone, we could parallelize the fetch+extract step
for 3-5x speedup. But sequential is easier to debug and reason about.
"""

import asyncio
import time
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.discovery_agent import generate_search_queries
from app.agents.extraction_agent import extract_programme
from app.config import get_settings
from app.models.research import ResearchRun
from app.services.eligibility_service import evaluate_eligibility
from app.services.opportunity_service import (
    save_source,
    upsert_opportunity,
    upsert_programme,
    upsert_university,
)
from app.services.profile_service import get_profile_snapshot
from app.services.scoring_service import score_opportunity
from app.tools.page_fetch import fetch_page
from app.tools.web_search import search_web
from app.tools.base import ToolError

logger = structlog.get_logger(__name__)


async def run_research_cycle(
    db: AsyncSession,
    user_email: str,
    max_queries: int = 5,
    max_urls_per_query: int = 3,
    dry_run: bool = False,
) -> ResearchRun:
    """
    Run a full research cycle for a user.

    Args:
        db: Database session
        user_email: The user's email (used to load their profile)
        max_queries: How many search queries to run (cost control)
        max_urls_per_query: How many URLs to fetch per query (cost control)
        dry_run: If True, don't save anything to the database (for testing)

    Returns:
        ResearchRun record with statistics and any errors
    """
    settings = get_settings()
    run_start = time.time()

    # Create a research run record to track this cycle
    research_run = ResearchRun(
        status="running",
        started_at=datetime.utcnow(),
    )
    if not dry_run:
        db.add(research_run)
        await db.flush()

    errors = []
    opportunities_found = 0
    opportunities_updated = 0
    pages_fetched = 0
    queries_generated = 0
    search_calls = 0

    try:
        # ── Step 1: Load profile ──────────────────────────────────────────
        logger.info("research_cycle_started", user=user_email)
        profile = await get_profile_snapshot(db, user_email)
        if not profile:
            raise ValueError(f"No profile found for {user_email}")

        # Load user ID for opportunity creation
        from app.services.profile_service import get_user_by_email
        user = await get_user_by_email(db, user_email)

        # ── Step 2: Generate search queries ──────────────────────────────
        logger.info("generating_queries")
        queries = generate_search_queries(profile, max_queries=max_queries)
        queries_generated = len(queries)
        logger.info("queries_generated", count=queries_generated)

        # ── Step 3-8: For each query, search → fetch → extract → save ────
        seen_urls: set[str] = set()  # deduplication across queries

        for query_idx, query in enumerate(queries[:max_queries]):
            logger.info(
                "processing_query",
                query_num=query_idx + 1,
                total=min(max_queries, queries_generated),
                query=query[:60],
            )

            # Search the web
            try:
                search_response = search_web(
                    query=query,
                    num_results=max_urls_per_query * 2,  # fetch extra, we'll filter
                )
                search_calls += 1
            except ToolError as e:
                logger.warning("search_failed", query=query[:60], error=str(e))
                errors.append({
                    "stage": "search",
                    "query": query[:80],
                    "error": str(e),
                })
                continue

            # Process each search result URL
            urls_processed_this_query = 0
            for result in search_response.results:
                if urls_processed_this_query >= max_urls_per_query:
                    break

                url = result.url

                # Skip duplicates
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Skip non-programme pages (job boards, news, etc.)
                skip_domains = [
                    "linkedin.com", "facebook.com", "twitter.com",
                    "reddit.com", "quora.com", "youtube.com",
                    "wikipedia.org", "indeed.com",
                ]
                if any(domain in url for domain in skip_domains):
                    continue

                # Fetch the page
                logger.info("fetching_page", url=url[:80])
                try:
                    page = fetch_page(url)
                    pages_fetched += 1
                except ToolError as e:
                    logger.warning("page_fetch_failed", url=url[:80], error=str(e))
                    errors.append({
                        "stage": "fetch",
                        "url": url[:100],
                        "error": str(e),
                    })
                    continue

                # Skip pages with too little content (likely not a programme page)
                if page.word_count < 100:
                    logger.debug("page_too_short", url=url[:80], words=page.word_count)
                    continue

                # Extract programme data
                logger.info("extracting_programme", url=url[:80])
                try:
                    extracted = extract_programme(
                        content=page.markdown,
                        url=url,
                    )
                except Exception as e:
                    logger.error("extraction_failed", url=url[:80], error=str(e))
                    errors.append({
                        "stage": "extraction",
                        "url": url[:100],
                        "error": str(e),
                    })
                    continue

                # Skip low-confidence extractions
                if extracted.confidence_overall < 0.3:
                    logger.debug(
                        "extraction_low_confidence",
                        url=url[:80],
                        confidence=extracted.confidence_overall,
                    )
                    continue

                # Skip if we couldn't extract a programme name
                if not extracted.programme_name:
                    logger.debug("extraction_no_programme_name", url=url[:80])
                    continue

                # Evaluate eligibility
                eligibility = evaluate_eligibility(extracted, profile)

                # Score the opportunity
                score = score_opportunity(extracted, profile, eligibility)

                logger.info(
                    "opportunity_evaluated",
                    programme=extracted.programme_name,
                    university=extracted.university_name,
                    eligibility=eligibility.status.value,
                    score=score.total_score,
                )

                # Skip German universities — excluded by user preference
                # Check URL and university name since ExtractedProgramme has no country field
                _uni = (extracted.university_name or "").lower()
                _is_german = (
                    ".de/" in url.lower()
                    or url.lower().endswith(".de")
                    or "germany" in _uni
                    or " uni " in _uni and any(
                        city in _uni for city in [
                            "berlin", "munich", "hamburg", "cologne", "frankfurt",
                            "stuttgart", "düsseldorf", "dortmund", "dresden",
                        ]
                    )
                )
                if _is_german:
                    logger.info(
                        "skipping_excluded_country",
                        country="Germany",
                        programme=extracted.programme_name,
                        url=url[:80],
                    )
                    continue

                # Save to database (unless dry run)
                if not dry_run:
                    try:
                        # Save source record
                        from app.tools.page_fetch import _compute_hash
                        content_hash = _compute_hash(page.markdown)
                        source = await save_source(
                            db,
                            url=url,
                            source_type="edu_database",
                            tier=4,
                            title=page.title,
                            content_hash=content_hash,
                        )

                        # Save university
                        university = await upsert_university(
                            db,
                            name=extracted.university_name or "Unknown University",
                        )

                        # Save programme
                        programme, is_new_programme = await upsert_programme(
                            db,
                            extracted=extracted,
                            university=university,
                            source=source,
                        )

                        # Save opportunity
                        opportunity, is_new_opp = await upsert_opportunity(
                            db,
                            user_id=user.id,
                            programme=programme,
                            eligibility=eligibility,
                            score=score,
                            extracted=extracted,
                            source=source,
                        )

                        if is_new_opp:
                            opportunities_found += 1
                            # Evaluate and send notification
                            from app.services.notification_service import evaluate_and_notify
                            await evaluate_and_notify(
                                db=db,
                                user_id=user.id,
                                opportunity=opportunity,
                                is_new=True,
                            )
                        else:
                            opportunities_updated += 1

                        await db.commit()

                    except Exception as e:
                        logger.error("db_save_failed", url=url[:80], error=str(e))
                        await db.rollback()
                        errors.append({
                            "stage": "database",
                            "url": url[:100],
                            "error": str(e),
                        })
                        continue
                else:
                    # Dry run — just count
                    opportunities_found += 1

                urls_processed_this_query += 1

                # Respectful crawl delay between requests
                await asyncio.sleep(settings.crawl_delay_seconds)

    except Exception as e:
        logger.error("research_cycle_failed", error=str(e))
        errors.append({"stage": "orchestrator", "error": str(e)})
        if not dry_run:
            research_run.status = "failed"
        raise

    finally:
        # Always update the research run record
        elapsed = time.time() - run_start
        research_run.completed_at = datetime.utcnow()
        research_run.status = "completed" if not errors else "partial"
        research_run.queries_generated = queries_generated
        research_run.pages_fetched = pages_fetched
        research_run.opportunities_found = opportunities_found
        research_run.opportunities_updated = opportunities_updated
        research_run.search_calls = search_calls
        research_run.errors = errors if errors else None

        if not dry_run:
            try:
                await db.commit()
            except Exception:
                pass

        logger.info(
            "research_cycle_completed",
            status=research_run.status,
            queries=queries_generated,
            pages_fetched=pages_fetched,
            opportunities_found=opportunities_found,
            opportunities_updated=opportunities_updated,
            errors=len(errors),
            elapsed_seconds=round(elapsed, 1),
        )

    return research_run
