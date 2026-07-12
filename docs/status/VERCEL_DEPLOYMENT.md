# CareerPilot AI - Vercel Deployment Guide

This guide covers deploying the CareerPilot frontend to Vercel.

## Prerequisites

1. Vercel account
2. Backend deployed (recommended: on Render or similar)
3. GitHub repository

## Setup

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Link Project

```bash
cd /home/ubuntu/careerpilot
vercel login
vercel link
```

### 3. Set Environment Variables

In Vercel project settings, add:

```
NEXT_PUBLIC_API_URL=https://your-backend-url.com/api
```

### 4. Deploy

```bash
vercel --prod
```

## GitHub Actions (Auto-deploy)

The workflow is already configured. Add these secrets to your GitHub repo:

- `VERCEL_TOKEN` - Your Vercel API token
- `VERCEL_ORG_ID` - Your Vercel org ID
- `VERCEL_PROJECT_ID` - Your Vercel project ID

### Get Vercel Credentials

1. Go to https://vercel.com/account/settings
2. Copy your Org ID
3. Go to https://vercel.com/account/tokens
4. Create a new token with full scope

### Get Project ID

1. Run `vercel ls` to list projects
2. Copy the project ID

## Configuration Files

- `vercel.json` - Vercel deployment configuration
- `frontend/next.config.js` - Next.js config (auto-detects Vercel)
- `frontend/.env.local` - Environment variables

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Vercel FE     │────▶│  Backend API    │
│  (frontend)     │     │  (Render,etc)   │
└─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │   PostgreSQL    │
                        │   Redis/Celery  │
                        └─────────────────┘
```

## Troubleshooting

- **API 404s**: Check `NEXT_PUBLIC_API_URL` matches your backend
- **Build fails**: Run `cd frontend && npm run build` locally
- **CORS issues**: Ensure backend allows your Vercel domain