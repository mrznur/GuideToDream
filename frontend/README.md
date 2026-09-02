# GuideToDream — Frontend

Next.js 14 frontend for the GuideToDream personal European Masters intelligence agent.

## Stack
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui

## Development

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Environment

```bash
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL to your backend URL
```

## Deploy

Deploy to Vercel:
1. Import this repository
2. Set Root Directory to `frontend`
3. Add `NEXT_PUBLIC_API_URL=https://guidetodream.onrender.com`
4. Deploy
