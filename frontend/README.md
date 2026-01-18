# MeloVue Frontend

Next.js frontend for the MeloVue AI music video generation service.

## Project Structure

```
frontend/
├── app/
│   ├── globals.css       # Global styles and Tailwind config
│   ├── layout.tsx        # Root layout component
│   └── page.tsx          # Home page component
├── components/
│   └── ui/
│       └── button.tsx    # Shadcn button component
├── lib/
│   └── utils.ts          # Utility functions (cn helper)
├── public/
│   └── logo.png          # Logo asset
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── README.md
```

## Setup

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000)

## Features

- **Audio URL Input** - Paste a direct link to an MP3 file
- **Image URL Input** - Paste a link to a theme/style image
- **Generation Progress** - Real-time progress tracking
- **Video Playback** - Watch generated videos inline

## Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Animations
- **Lucide React** - Icons
- **Shadcn/ui** - Component library

## Styling

The app uses a clean, modern aesthetic with:
- Playfair Display serif font for headings
- DM Sans for body text
- Green accent color (#22c55e)
- Sharp corners (0 border-radius) for a distinctive look
