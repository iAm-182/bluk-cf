# Cloudflare Auto Signup

Automated Cloudflare account creation with **Workers AI API token generation**. Bypasses Cloudflare Turnstile CAPTCHA and WAF using headless browser automation.

## Features

- 🤖 **Automated Signup** — Creates Cloudflare accounts via headless browser
- 🔐 **Turnstile Bypass** — Solves Cloudflare Turnstile CAPTCHA using `nodriver` + OpenCV template matching
- 🎫 **Token Creation** — Automatically creates Account API Tokens with Workers AI permissions
- ✅ **Token Validation** — Verifies created tokens against Cloudflare API
- 📧 **Disposable Email** — Generates temp email addresses for registration
- 💾 **JSON Export** — Saves all results (account ID, API token, validation status)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  main.py (Orchestrator)              │
├─────────────┬──────────────┬───────────────┬────────┤
│ email_gen   │ signup_flow  │ token_creator │ output │
│ (jackmail)  │ (nodriver)   │ (Account API) │ (JSON) │
├─────────────┼──────────────┼───────────────┤        │
│ turnstile   │ OpenCV       │ nodriver UI   │        │
│ _bypass     │ verify_cf()  │ automation    │        │
└─────────────┴──────────────┴───────────────┴────────┘
```

## How It Works

### 1. Turnstile Bypass
```
Cloudflare Turnstile checkbox → OpenCV template matching (cv2.matchTemplate)
→ Calculate center coordinates → OS-level mouse_click() via nodriver
→ Poll for cf-turnstile-response token
```

**Key insight**: Standard CDP click events don't work on Turnstile (cross-origin iframe, sandboxed). The solution uses **OS-level mouse clicks** via `mouse_click(x, y)` which bypasses the iframe sandbox.

### 2. Signup Flow
```
1. Generate temp email via jackmail API
2. Navigate to dash.cloudflare.com/sign-up
3. Fill email + password
4. Solve Turnstile CAPTCHA (verify_cf)
5. Submit form via button[type="submit"]
6. Extract Account ID from redirect URL
```

### 3. Token Creation
```
1. Navigate to /{account_id}/api-tokens/create
2. Fill token name
3. Click "AI & Machine Learning" category
4. Select Workers AI permissions (Read + Edit)
5. Click "Review token" → "Create Token"
6. Extract cfut_* token from page
```

### 4. Validation
```
1. POST to /api/v4/accounts/{id}/workers/ai/models
2. Verify 200 OK + models list returned
3. Save to JSON with full metadata
```

## Requirements

- **Linux VPS** with Xvfb (`xvfb-run`)
- **Python 3.10+**
- **Google Chrome** installed
- **jackmail** instance (or compatible email API)
- **Proxy** (optional, for bypassing IP rate limits)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp config.example.json config.json
# Edit config.json with your settings

# Run
python main.py --accounts 5 --output results.json

# With proxy
python main.py --accounts 5 --proxy "http://user:pass@host:port" --output results.json
```

## Configuration

```json
{
    "mail_api": "https://mail.example.com/api/new_address",
    "mail_domain": "example.com",
    "proxy": null,
    "headless": false,
    "max_accounts": 10,
    "retry_attempts": 3,
    "token_name": "workers-ai-auto",
    "permissions": ["Workers AI"],
    "output_file": "results.json"
}
```

## Output Format

```json
[
    {
        "email": "cf12345@example.com",
        "password": "Cf123!@#xYz",
        "account_id": "a1b2c3d4e5f6...",
        "api_token": "cfut_xxxxxxxxxxxxxxxxxxxxxxxx",
        "token_valid": true,
        "workers_ai_models": 60,
        "created_at": "2026-07-03T22:00:00Z",
        "proxy_used": "186.220.38.103",
        "status": "full"
    }
]
```

## Rate Limits

| Metric | Value |
|--------|-------|
| Signups per IP | ~10-15 before block |
| Rate limit window | **2-24 hours** (varies) |
| cf_clearance duration | 30 min (single-use) |
| Recommended delay | 5-10 min between signups |

See [docs/RATE_LIMITS.md](docs/RATE_LIMITS.md) for detailed analysis.

## Known Limitations

1. **IP Rate Limiting** — Cloudflare limits signups per IP (~10-15)
2. **No Re-login** — Google OAuth redirect prevents email/password re-login
3. **Click Sensitivity** — Some React buttons require exact CDP mouse events
4. **Proxy Required** — For mass production, residential proxies needed

## Project Structure

```
cloudflare-auto-signup/
├── main.py                    # Entry point — orchestrator
├── config.example.json        # Configuration template
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── LICENSE                    # MIT License
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── email_generator.py     # Temp email API client
│   ├── turnstile_bypass.py    # OpenCV Turnstile solver
│   ├── signup_flow.py         # Cloudflare signup automation
│   ├── token_creator.py       # Account API Token creation
│   ├── token_validator.py     # Token validation via Workers AI API
│   └── utils.py               # Shared utilities
├── scripts/
│   ├── setup.sh               # VPS setup script
│   └── batch_runner.sh        # Batch execution with proxy rotation
├── docs/
│   ├── RATE_LIMITS.md         # Rate limit analysis
│   ├── WAF_BYPASS.md          # WAF bypass techniques documented
│   └── ARCHITECTURE.md        # Technical deep-dive
└── tests/
    └── test_token_validator.py # Token validation tests
```

## Disclaimer

This tool is for **educational and authorized security research** only. Use responsibly and in compliance with Cloudflare's Terms of Service. The authors are not responsible for misuse.

## License

MIT License — See [LICENSE](LICENSE)
