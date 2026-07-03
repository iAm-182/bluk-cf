# Technical Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (Orchestrator)                   │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  Email    │    │   Signup     │    │   Token Creator      │  │
│  │ Generator │───▶│   Flow       │───▶│   (Account API)      │  │
│  │ (HTTP)    │    │ (nodriver)   │    │   (nodriver)         │  │
│  └──────────┘    └──────┬───────┘    └──────────┬───────────┘  │
│                         │                       │              │
│                  ┌──────▼───────┐    ┌──────────▼───────────┐  │
│                  │  Turnstile   │    │   Token Validator    │  │
│                  │  Bypass      │    │   (HTTP/REST)        │  │
│                  │  (OpenCV)    │    │                      │  │
│                  └──────────────┘    └──────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Output: results.json                  │  │
│  │  {email, password, account_id, api_token, token_valid}   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Email Generator
- HTTP client calling jackmail-compatible API
- Supports multiple domains
- Returns JWT for inbox access

### 2. Signup Flow
- nodriver browser automation
- Handles Turnstile via verify_cf()
- Extracts Account ID from redirect URL
- Error detection (rate limit, validation)

### 3. Turnstile Bypass
- OpenCV template matching for checkbox detection
- OS-level mouse_click() via CDP (bypasses iframe sandbox)
- Polls for cf-turnstile-response hidden input
- Falls back to color-based detection if no template

### 4. Token Creator
- Navigates to Account API Tokens creation page
- Uses evaluate() for React-compatible button clicks
- Multi-strategy click: JS → nodriver.find → CDP mouse
- Extracts cfut_* token from page content

### 5. Token Validator
- REST API calls to Cloudflare v4
- Verifies token status (active/inactive)
- Counts available Workers AI models
- No browser needed — pure HTTP

## Data Flow

```
Email API ──▶ Signup (browser) ──▶ Dashboard (browser) ──▶ API (HTTP)
     │              │                      │                    │
     ▼              ▼                      ▼                    ▼
  email+jwt    account_id              cfut_token         validation
     │              │                      │                    │
     └──────────────┴──────────────────────┴────────────────────┘
                                    │
                                    ▼
                            results.json
```

## Security Considerations

1. **No credentials stored in code** — config.json is gitignored
2. **Temp emails** — disposable, no PII
3. **Tokens in JSON** — protect results.json (add to .gitignore)
4. **Proxy auth** — use env vars for production

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| nodriver | ≥0.38 | Chrome automation (undetected) |
| opencv-python-headless | ≥4.8 | Template matching for Turnstile |
| httpx | ≥0.25 | HTTP client (email API, validation) |
| Pillow | ≥10.0 | Image processing |
