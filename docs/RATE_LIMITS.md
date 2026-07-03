# Cloudflare Rate Limit Analysis

## Observed Behavior (July 2026)

### Signup Rate Limits

| Metric | Server IP (70.x) | Proxy IP (186.x) |
|--------|-------------------|-------------------|
| Successful signups before block | ~10-12 | ~3-4 |
| Error message | "You are unable to sign up at this time" | Same |
| Recovery time (observed) | **2-6 hours** | **1-3 hours** |
| Boterdrop clearance | Failed after block (60s timeout) | Same |

### How Rate Limiting Works

Cloudflare uses **IP-based rate limiting** for the signup flow:

1. **Per-IP counter**: Each IP gets ~10-15 signup attempts
2. **Window**: The counter resets after **2-24 hours** (varies)
3. **Escalation**: Repeated blocks may increase the cooldown
4. **Fingerprinting**: Cloudflare also fingerprints the browser; changing IP alone may not be enough
5. **Proxy detection**: Datacenter proxies are detected faster than residential

### API Token Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/api/v4/user/tokens` | WAF-blocked from XHR (requires dashboard UI) |
| `/api/v4/accounts/{id}/workers/ai/models` | Standard API rate limit (1200 req/5min) |
| Token creation UI | No observed rate limit |

### Cloudflare WAF Challenge

| Component | Behavior |
|-----------|----------|
| Turnstile CAPTCHA | Appears on signup page; solvable with nodriver+OpenCV |
| cf_clearance cookie | Required for API calls; single-use, 30 min TTL |
| cf_clearance + curl_cffi | **Does NOT work** — cookie is TLS-fingerprint-bound |
| cf_clearance + Camoufox | Works (Boterdrop-Solver uses this) |

### Rate Limit Recovery Timeline

```
Hour 0:     Signup works normally
Hour 0-1:   First rate limit hit (~10 signups)
Hour 1-2:   Still blocked, Boterdrop clearance fails
Hour 2-4:   Partial recovery (some IPs recover faster)
Hour 4-6:   Most IPs recover
Hour 6-24:  Full recovery guaranteed
```

### Strategies to Minimize Rate Limits

1. **Use residential proxies** — Higher threshold before blocking
2. **Add delays** — 5-10 minutes between signups
3. **Rotate IPs** — Use multiple proxies
4. **Browser fingerprint rotation** — Different User-Agent per signup
5. **Timing** — Avoid burst patterns; spread signups over hours

### Proxy Requirements

| Type | Signups before block | Cost |
|------|---------------------|------|
| Direct VPS IP | ~10-15 | Free |
| Datacenter proxy | ~3-5 | $1-3/proxy |
| Residential proxy | ~50-100 | $5-15/GB |
| Mobile proxy | ~100+ | $20-50/day |

### Recommendations

For **development/testing**: Use direct VPS IP, create 5-10 accounts, wait 6 hours.

For **production**: Use residential proxy rotation with 5-10 minute delays.

For **maximum throughput**: Multiple VPS IPs + residential proxies + scheduled runs.
