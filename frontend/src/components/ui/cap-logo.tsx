/**
 * CapLogo
 * -------
 * Broken-glass / faceted sky-blue graduation cap SVG.
 * Each polygon is a shard of the cap silhouette, with
 * slightly varying opacity to create the fractured-glass look.
 *
 * Props:
 *   size   — overall size in px (default 40)
 *   glow   — whether to render the outer glow ring (default true)
 *   mono   — if true, all shards same opacity (cleaner for small sizes)
 */

interface CapLogoProps {
  size?: number
  glow?: boolean
  mono?: boolean
  className?: string
}

export default function CapLogo({ size = 40, glow = true, mono = false, className }: CapLogoProps) {
  // All coordinates are on a 100×100 viewBox.
  // The cap silhouette is built from shards — each polygon is a "broken pane".
  // Sky-blue fills at varying opacities create the faceted glass effect.
  // Edge strokes at low opacity give the crack lines.

  const S = "#5bbcf8"   // sky base
  const B = "#9ddcff"   // sky bright highlight
  const D = "#1d6fa8"   // sky deep shadow
  const E = "#3a9de0"   // sky mid

  // Shard opacity levels — "light through glass"
  const o = (v: number) => mono ? 0.82 : v

  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      className={className}
      aria-label="GuideToDream graduation cap"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        {/* Outer glow filter */}
        <filter id="capGlow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>

        {/* Inner glow for highlight shards */}
        <filter id="shardGlow" x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation="1.2" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>

        {/* Clip to cap outline so nothing bleeds outside */}
        <clipPath id="capClip">
          {/* Board: flat diamond top */}
          <polygon points="50,12 94,32 50,52 6,32" />
          {/* Body: trapezoidal base */}
          <polygon points="50,52 78,42 78,68 50,78 22,68 22,42" />
          {/* Tassel drop */}
          <rect x="78" y="32" width="6" height="42" rx="2" />
          <circle cx="84" cy="76" r="5" />
        </clipPath>
      </defs>

      {/* ── Glow halo (behind everything) */}
      {glow && (
        <g filter="url(#capGlow)">
          <ellipse cx="50" cy="44" rx="42" ry="36"
            fill="none"
            stroke={S}
            strokeWidth="0.5"
            opacity="0.22"
          />
        </g>
      )}

      {/* ── All shards clipped to cap silhouette ─────────────────────── */}
      <g clipPath="url(#capClip)">

        {/* ── BOARD (diamond top face) — broken into 8 shards ────────── */}

        {/* Top-left quadrant, shard A — large */}
        <polygon points="50,12 28,22 6,32 50,32"
          fill={D} opacity={o(0.75)} />

        {/* Top-left quadrant, shard B — sliver */}
        <polygon points="28,22 50,12 42,28"
          fill={B} opacity={o(0.55)} />

        {/* Top-right quadrant, shard A */}
        <polygon points="50,12 72,22 94,32 50,32"
          fill={E} opacity={o(0.68)} />

        {/* Top-right quadrant, shard B — highlight sliver */}
        <polygon points="72,22 94,32 80,28"
          fill={B} opacity={o(0.45)} />

        {/* Bottom-left of board */}
        <polygon points="6,32 50,32 28,42 6,32"
          fill={S} opacity={o(0.88)} />

        {/* Bottom-right of board */}
        <polygon points="50,32 94,32 72,42 50,52"
          fill={D} opacity={o(0.60)} />

        {/* Center of board */}
        <polygon points="50,32 72,42 50,52 28,42"
          fill={B} opacity={o(0.50)} filter="url(#shardGlow)" />

        {/* Micro crack lines on board surface */}
        <line x1="50" y1="12" x2="50" y2="52" stroke={S} strokeWidth="0.4" opacity="0.35" />
        <line x1="6"  y1="32" x2="94" y2="32" stroke={B} strokeWidth="0.35" opacity="0.28" />
        <line x1="28" y1="22" x2="72" y2="42" stroke={S} strokeWidth="0.3" opacity="0.22" />
        <line x1="72" y1="22" x2="28" y2="42" stroke={B} strokeWidth="0.3" opacity="0.18" />

        {/* ── BODY (trapezoidal base under board) — 6 shards ──────────── */}

        {/* Left face shard A */}
        <polygon points="22,42 50,52 38,58 22,54"
          fill={D} opacity={o(0.80)} />

        {/* Left face shard B */}
        <polygon points="22,54 38,58 22,68"
          fill={S} opacity={o(0.65)} />

        {/* Left face shard C */}
        <polygon points="22,68 38,58 50,78"
          fill={E} opacity={o(0.50)} />

        {/* Right face shard A */}
        <polygon points="78,42 50,52 62,58 78,54"
          fill={E} opacity={o(0.70)} />

        {/* Right face shard B */}
        <polygon points="78,54 62,58 78,68"
          fill={D} opacity={o(0.82)} />

        {/* Right face shard C */}
        <polygon points="78,68 62,58 50,78"
          fill={S} opacity={o(0.58)} />

        {/* Center front shard */}
        <polygon points="50,52 62,58 50,78 38,58"
          fill={B} opacity={o(0.42)} filter="url(#shardGlow)" />

        {/* Body crack lines */}
        <line x1="50" y1="52" x2="50" y2="78" stroke={B} strokeWidth="0.4" opacity="0.30" />
        <line x1="22" y1="54" x2="78" y2="54" stroke={S} strokeWidth="0.3" opacity="0.22" />
        <line x1="38" y1="58" x2="62" y2="58" stroke={B} strokeWidth="0.35" opacity="0.28" />

        {/* ── TASSEL ──────────────────────────────────────────────────── */}

        {/* Tassel cord — two shards */}
        <rect x="78" y="32" width="6" height="22" rx="1"
          fill={S} opacity={o(0.70)} />
        <rect x="78" y="54" width="6" height="20" rx="1"
          fill={D} opacity={o(0.85)} />

        {/* Tassel ball — faceted circle */}
        <circle cx="84" cy="76" r="5" fill={E} opacity={o(0.78)} />
        <polygon points="84,71 89,76 84,81 79,76"
          fill={B} opacity={o(0.50)} />

      </g>

      {/* ── Outline / crack strokes on cap silhouette edge ──────────── */}
      {/* Board outline */}
      <polygon points="50,12 94,32 50,52 6,32"
        fill="none"
        stroke={S}
        strokeWidth="0.6"
        opacity="0.50"
      />
      {/* Body outline */}
      <polygon points="50,52 78,42 78,68 50,78 22,68 22,42"
        fill="none"
        stroke={S}
        strokeWidth="0.6"
        opacity="0.40"
      />
      {/* Tassel cord outline */}
      <line x1="81" y1="32" x2="81" y2="76" stroke={S} strokeWidth="0.5" opacity="0.35" />
      {/* Tassel ball outline */}
      <circle cx="84" cy="76" r="5"
        fill="none" stroke={S} strokeWidth="0.6" opacity="0.45" />
    </svg>
  )
}
