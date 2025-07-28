# Brikli Tenant Portal

React frontend application for the Brikli Tenant Portal, providing tenants with access to their rental information, maintenance requests, and property management features.

## Overview

The Tenant Portal is built with React 19, Vite, and Tailwind CSS, offering a modern and responsive interface for tenant interactions with the Brikli property management platform.

## Features

- **Authentication**: Secure login via Supabase Auth
- **Dashboard**: Overview of tenant information and property details
- **Maintenance Requests**: Submit and track maintenance issues
- **Lease Information**: Access lease documents and terms
- **Payment History**: View rental payment records

## Tech Stack

- **Frontend**: React 19 + Vite + Tailwind CSS v4
- **Authentication**: Supabase Auth with JWT tokens
- **Routing**: React Router v7
- **API Integration**: RESTful API calls to Brikli Backend
- **Deployment**: Docker + Nginx

## Development Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Set up environment variables**:
   Create a `.env` file with:
   ```env
   VITE_API_URL=http://localhost:8000
   VITE_SUPABASE_URL=your_supabase_url
   VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

## Building for Production

```bash
npm run build
npm run preview
```

## Docker Deployment

The application is containerized with a multi-stage Docker build:

```bash
docker build -t brikli-tenant-frontend .
docker run -p 4173:80 brikli-tenant-frontend
```

## Project Structure

```
src/
├── components/       # Reusable UI components
├── pages/           # Page-level components
├── contexts/        # React context providers
├── utils/           # API utilities and helpers
└── styles/          # Global styles and themes
```

## Related Services

- **Backend API**: Located in `/Backend` directory
- **Landlord Portal**: Located in `/Frontend` directory
- **Database**: Supabase PostgreSQL
