# Mariwasa Automated Resume Analysis — Frontend (Next.js TypeScript)

The frontend application is built with **Next.js (App Router)** and **TypeScript**, powered by Tailwind CSS v4 and Redux Toolkit.

## Architecture & Project Structure

The project follows standard Next.js App Router conventions:

```
frontend/
├── dev.mjs                 # Dev server runner with host/port flag handling
├── next.config.mjs         # Next.js standalone configuration & API rewrites
├── postcss.config.mjs      # Tailwind CSS PostCSS plugin configuration
├── package.json            # Scripts & dependencies
├── tsconfig.json           # TypeScript configuration with path aliases (@/*)
├── public/                 # Static assets (images, icons, etc.)
│   └── assets/             # Brand logos, banners, illustrations
└── src/
    ├── app/                # Next.js App Router route segments
    │   ├── layout.tsx      # Root layout
    │   ├── providers.tsx   # Redux, Navigation, Helmet, and Toast providers
    │   ├── globals.css     # Global styles & Tailwind imports
    │   ├── page.tsx        # Landing / Home page
    │   ├── (public)/       # Public routes: /aboutpage, /careerspage, /smart-upload, etc.
    │   ├── (auth)/         # Auth routes: /login, /register, /forgot-password, etc.
    │   ├── admin/          # Admin portal routes: /admin/dashboard, /admin/users, etc.
    │   ├── hr/             # HR portal routes: /hr/dashboard, /hr/screeningportal, etc.
    │   └── candidate/      # Candidate portal routes: /candidate/dashboard, etc.
    ├── views/              # Page view implementations
    ├── components/         # Reusable UI components
    ├── redux/              # Redux Toolkit store, slices, and RTK Query API slice
    ├── services/           # Axios API services and backend endpoints
    ├── types/              # TypeScript interfaces and type definitions
    └── utils/              # Navigation adapter, formatting, and export helpers
```

## Available Scripts

- `npm run dev`: Starts the Next.js development server (default port: `5173`).
- `npm run build`: Generates an optimized production build (`standalone`).
- `npm run start`: Runs the production server on port `5173`.
- `npm run lint`: Runs code linting.

## Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API base path or URL (default: `/api` in production, `http://localhost:8000` in dev).
- `NEXT_PUBLIC_WS_URL`: WebSocket base URL for real-time notifications and chat.
