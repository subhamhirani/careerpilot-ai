# DNS & HTTPS Configuration Guide

## Current State
- **Public IP**: `3.109.213.250`
- **Reverse Proxy**: Caddy (auto-SSL when domain is added)
- **HTTP**: ✅ Working on port 80
- **HTTPS**: ❌ Needs domain name for Caddy to request Let's Encrypt certificate

## Step 1: Register / Use a Domain

Choose any domain registrar (e.g., Namecheap, GoDaddy, Cloudflare, AWS Route 53).

## Step 2: Create DNS Records

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | `@` | `3.109.213.250` | 300 |
| A | `www` | `3.109.213.250` | 300 |
| A | `api` | `3.109.213.250` | 300 |

Wait for DNS propagation (usually 5-30 minutes, up to 24 hours).

### Verify propagation:
```bash
dig +short yourdomain.com
# Expected: 3.109.213.250
```

## Step 3: Configure Caddy

The Caddyfile at `/home/ubuntu/careerpilot/Caddyfile` handles auto-SSL.

Minimal Caddyfile:
```
yourdomain.com {
    reverse_proxy localhost:3000
}

api.yourdomain.com {
    reverse_proxy localhost:7899
}
```

Caddy automatically:
1. Detects the domain
2. Requests a Let's Encrypt certificate
3. Serves HTTPS on 443
4. Redirects HTTP → HTTPS

## Step 4: Update Next.js Environment

Edit `/home/ubuntu/careerpilot/frontend/.env.local` (or add to `.env`):
```
NEXT_PUBLIC_APP_URL=https://yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

Rebuild and restart frontend:
```bash
cd /home/ubuntu/careerpilot/frontend
npm ci --legacy-peer-deps
npm run build
cd ../
docker compose up -d --build frontend
```

## Step 5: Verify SSL

```bash
# Check certificate
curl -vI https://yourdomain.com 2>&1 | grep -E "subject|issuer|SSL"

# Test API
curl https://api.yourdomain.com/health
```

## Why Domain is Needed

1. **HTTPS**: Let's Encrypt requires a domain to issue certificates
2. **Next.js Server Actions**: Enforced origin check fails with raw IP + port
3. **Production readiness**: Professional URL for resumes/interviews
4. **Monitoring**: Uptime-Kuma can monitor by domain name

## Free Domain Options

If you don't want to buy a domain yet:

1. **No-IP.com**: Free dynamic DNS subdomain
2. **DuckDNS**: Free subdomain (e.g., `yourname.duckdns.org`)
3. **Freenom**: Free `.tk`, `.ml`, `.ga`, `.cf`, `.gq` domains (check availability)

Choose any, then follow Steps 2-5 above.

## Troubleshooting

### Caddy fails to get certificate
```bash
# Check Caddy logs
docker logs careerpilot-caddy --tail 50

# Ensure port 443 is open in AWS Security Group
# Ensure no other process is using port 443
```

### DNS not propagating
```bash
# Flush local DNS (Linux)
sudo systemd-resolve --flush-caches  # or
sudo service nscd restart

# Use online checker
# https://dnschecker.org
```

### Next.js still shows IP error after domain
```bash
# Clear Next.js cache
rm -rf /home/ubuntu/careerpilot/frontend/.next

# Rebuild with fresh env
docker compose up -d --build frontend
```

## Cost

| Item | Cost |
|------|------|
| Domain (e.g., Namecheap .com) | ~$10-15/year |
| Let's Encrypt SSL | Free |
| Caddy | Free |
| **Total** | **~$10-15/year** |

---

*Guide generated: 2026-07-03*
