"""Shared utilities for Cloudflare Auto Signup."""

import json
import random
import string
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_password(length: int = 12) -> str:
    """Generate a strong password: Cf### + special chars + mixed case + digits."""
    digits = "".join(random.choices(string.digits, k=3))
    specials = random.choices("!@#$%^&*", k=2)
    letters = random.choices(string.ascii_letters, k=length - 5 - 2)
    base = f"Cf{digits}" + "".join(letters) + "".join(specials)
    # Shuffle middle portion
    chars = list(base[2:])
    random.shuffle(chars)
    return "Cf" + "".join(chars)


def generate_username(prefix: str = "cf", length: int = 5) -> str:
    """Generate a random username like cf12345."""
    return f"{prefix}{random.randint(10**(length-1), 10**length - 1)}"


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    path = Path(config_path)
    if not path.exists():
        path = Path(config_path.replace(".json", ".example.json"))
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(path) as f:
        return json.load(f)


def save_result(result: dict, output_file: str = "results.json") -> None:
    """Append a result to the JSON output file."""
    results = []
    path = Path(output_file)
    if path.exists():
        try:
            with open(path) as f:
                results = json.load(f)
        except (json.JSONDecodeError, ValueError):
            results = []

    results.append(result)
    with open(path, "w") as f:
        json.dump(results, f, indent=2)


def load_results(output_file: str = "results.json") -> list:
    """Load existing results from JSON file."""
    path = Path(output_file)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []


def timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def wait_with_progress(seconds: int, message: str = "Waiting") -> None:
    """Print countdown timer."""
    for remaining in range(seconds, 0, -1):
        print(f"\r  {message}... {remaining}s remaining", end="", flush=True)
        time.sleep(1)
    print()


def format_account(result: dict) -> str:
    """Format account info for display."""
    email = result.get("email", "unknown")
    account_id = result.get("account_id", "N/A")[:16]
    token = result.get("api_token", "N/A")
    valid = "✅" if result.get("token_valid") else "❌"
    token_preview = f"{token[:20]}..." if token.startswith("cfut_") else "N/A"
    return f"  {email} | {account_id}... | {token_preview} | {valid}"
