#!/usr/bin/env python3
"""
Cloudflare Auto Signup — Main Orchestrator

Automates the full pipeline:
1. Generate temp email
2. Sign up for Cloudflare account (with Turnstile bypass)
3. Create Account API Token (Workers AI permissions)
4. Validate token against Workers AI API
5. Save results to JSON

Usage:
    python main.py                          # Create 1 account
    python main.py --accounts 5             # Create 5 accounts
    python main.py --proxy http://user:pass@host:port
    python main.py --config custom.json
    python main.py --validate-only --token cfut_xxx --account-id xxx

Requirements:
    - Linux with Xvfb (xvfb-run)
    - Python 3.10+
    - Google Chrome installed
    - nodriver, opencv-python-headless, httpx
"""

import argparse
import asyncio
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import nodriver as uc

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.email_generator import EmailGenerator
from src.signup_flow import signup
from src.token_creator import create_token
from src.token_validator import validate_token
from src.utils import (
    generate_password,
    generate_username,
    load_config,
    save_result,
    load_results,
    timestamp,
    wait_with_progress,
    format_account,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Automated Cloudflare account creation with Workers AI tokens"
    )
    parser.add_argument(
        "--accounts", "-n", type=int, default=1,
        help="Number of accounts to create (default: 1)"
    )
    parser.add_argument(
        "--config", "-c", type=str, default="config.json",
        help="Config file path (default: config.json)"
    )
    parser.add_argument(
        "--proxy", "-p", type=str, default=None,
        help="Proxy URL (http://user:pass@host:port)"
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output JSON file (default: from config)"
    )
    parser.add_argument(
        "--delay", "-d", type=int, default=None,
        help="Delay between accounts in seconds (default: from config)"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--validate-only", action="store_true",
        help="Only validate an existing token (requires --token and --account-id)"
    )
    parser.add_argument("--token", type=str, help="Token to validate")
    parser.add_argument("--account-id", type=str, help="Account ID for validation")
    parser.add_argument(
        "--retry", type=int, default=3,
        help="Number of retry attempts per account (default: 3)"
    )
    return parser.parse_args()


async def create_account(
    config: dict,
    proxy: str = None,
    headless: bool = False,
    browser: uc.Browser = None,
) -> dict:
    """
    Create a single Cloudflare account with API token.

    Returns:
        dict with account info and token (or error)
    """
    # Generate credentials
    username = generate_username()
    domain = random.choice(config["mail_domains"])
    password = generate_password()
    token_name = config.get("token_name", "workers-ai-auto")
    mail_api = config["mail_api"]

    # Create temp email
    email_gen = EmailGenerator(mail_api, config["mail_domains"])
    try:
        mail = email_gen.create(username=username, domain=domain)
        email = mail["email"]
    except Exception as e:
        return {"status": "error", "error": f"Email creation failed: {e}", "email": f"{username}@{domain}"}
    finally:
        email_gen.close()

    print(f"  📧 {email}")

    # Use provided browser or create new one
    own_browser = False
    if browser is None:
        browser = await uc.start(
            headless=headless,
            lang="en-US",
            proxy=proxy,
        )
        own_browser = True

    try:
        # Phase 1: Signup
        print("  [1/3] Signing up...")
        page = await browser.get("https://dash.cloudflare.com/sign-up")
        signup_result = await signup(page, email, password)

        if not signup_result.success:
            return {
                "status": "error",
                "email": email,
                "password": password,
                "error": f"Signup failed: {signup_result.error}",
            }

        account_id = signup_result.account_id
        print(f"  🆔 Account ID: {account_id}")

        # Phase 2: Token creation
        print("  [2/3] Creating API token...")
        page2 = await browser.get(f"https://dash.cloudflare.com/{account_id}/api-tokens/create")
        token_result = await create_token(page2, account_id, token_name)

        api_token = token_result.token if token_result.success else ""
        if api_token:
            print(f"  🔑 Token: {api_token[:30]}...")
        else:
            print(f"  ⚠️ Token creation failed: {token_result.error}")

        # Phase 3: Validation (even without token, save the account)
        token_valid = False
        model_count = 0
        if api_token:
            print("  [3/3] Validating token...")
            validation = validate_token(api_token, account_id)
            token_valid = validation.valid
            model_count = validation.workers_ai_models
            if token_valid:
                print(f"  ✅ Valid! {model_count} Workers AI models available")
            else:
                print(f"  ❌ Validation failed: {validation.error}")
        else:
            print("  [3/3] Skipping validation (no token)")

        result = {
            "email": email,
            "password": password,
            "jwt": mail.get("jwt", ""),
            "account_id": account_id,
            "api_token": api_token,
            "token_valid": token_valid,
            "workers_ai_models": model_count,
            "token_name": token_name,
            "status": "full" if token_valid else ("signup_only" if account_id else "error"),
            "created_at": timestamp(),
            "proxy_used": proxy or "direct",
        }
        return result

    except Exception as e:
        return {
            "status": "error",
            "email": email,
            "password": password,
            "error": str(e),
            "created_at": timestamp(),
        }
    finally:
        if own_browser:
            browser.stop()


async def main():
    args = parse_args()

    # Load config
    config = load_config(args.config)
    proxy = args.proxy or config.get("proxy")
    output_file = args.output or config.get("output_file", "results.json")
    delay = args.delay if args.delay is not None else config.get("delay_between_accounts", 300)
    num_accounts = args.accounts
    max_retry = args.retry

    # Validate-only mode
    if args.validate_only:
        if not args.token or not args.account_id:
            print("❌ --validate-only requires --token and --account-id")
            sys.exit(1)
        print("🔍 Validating token...")
        result = validate_token(args.token, args.account_id)
        print(f"  Valid: {result.valid}")
        print(f"  Models: {result.workers_ai_models}")
        if result.error:
            print(f"  Error: {result.error}")
        sys.exit(0 if result.valid else 1)

    print("=" * 60)
    print("☁️  Cloudflare Auto Signup — Workers AI Token Creator")
    print("=" * 60)
    print(f"  Accounts to create: {num_accounts}")
    print(f"  Proxy: {proxy or 'None (direct)'}")
    print(f"  Delay between: {delay}s")
    print(f"  Output: {output_file}")
    print(f"  Headless: {args.headless or config.get('headless', False)}")
    print("=" * 60)

    # Create accounts
    created = 0
    failed = 0
    results = load_results(output_file)

    for i in range(num_accounts):
        print(f"\n{'─' * 50}")
        print(f"  Account {i + 1}/{num_accounts}")
        print(f"{'─' * 50}")

        success = False
        for attempt in range(max_retry):
            if attempt > 0:
                print(f"  ↻ Retry {attempt}/{max_retry - 1}")
                await asyncio.sleep(30)

            result = await create_account(
                config=config,
                proxy=proxy,
                headless=args.headless or config.get("headless", False),
            )

            if result.get("status") == "full":
                success = True
                break
            elif result.get("status") == "signup_only":
                # Account created but no token — still save
                success = True
                break
            elif "rate" in str(result.get("error", "")).lower() or \
                 "unable" in str(result.get("error", "")).lower():
                print(f"  ⚠️ Rate limited — waiting {delay}s before retry")
                wait_with_progress(delay, "Rate limit cooldown")
            else:
                print(f"  ❌ Error: {result.get('error', 'unknown')}")

        # Save result
        save_result(result, output_file)
        results.append(result)

        if success:
            created += 1
            print(f"\n  ✅ {format_account(result)}")
        else:
            failed += 1
            print(f"\n  ❌ Failed: {result.get('error', 'unknown')}")

        # Delay between accounts (skip on last)
        if i < num_accounts - 1 and success:
            print(f"\n  ⏳ Waiting {delay}s before next account...")
            wait_with_progress(delay, "Cooldown")

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"📊 Results: {created} created, {failed} failed")
    print(f"💾 Saved to: {output_file}")
    if created > 0:
        print(f"\nAccounts:")
        for r in results[-created:]:
            print(format_account(r))
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
