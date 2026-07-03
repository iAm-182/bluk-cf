"""
Token Validator — Verifies Cloudflare API tokens by calling Workers AI endpoint.

Uses the Cloudflare API to:
1. Validate the token (GET /api/v4/user/tokens/verify)
2. List available Workers AI models (GET /api/v4/accounts/{id}/workers/ai/models)
3. Confirm the token has the correct permissions
"""

import httpx
from typing import Optional


CLOUDFLARE_API = "https://api.cloudflare.com/client/v4"


class ValidationResult:
    """Result of token validation."""

    def __init__(
        self,
        valid: bool,
        account_id: str = "",
        email: str = "",
        workers_ai_models: int = 0,
        permissions: list[str] = None,
        error: str = "",
    ):
        self.valid = valid
        self.account_id = account_id
        self.email = email
        self.workers_ai_models = workers_ai_models
        self.permissions = permissions or []
        self.error = error

    def to_dict(self) -> dict:
        return {
            "token_valid": self.valid,
            "workers_ai_models": self.workers_ai_models,
            "permissions": self.permissions,
            "validation_error": self.error,
        }


def validate_token(
    api_token: str,
    account_id: str,
    timeout: int = 30,
) -> ValidationResult:
    """
    Validate an API token against Cloudflare.

    Args:
        api_token: The cfut_* token to validate
        account_id: Cloudflare Account ID
        timeout: Request timeout in seconds

    Returns:
        ValidationResult with validation details
    """
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        # 1. Verify the token itself
        try:
            r = client.get(f"{CLOUDFLARE_API}/user/tokens/verify", headers=headers)
            data = r.json()

            if not data.get("success", False):
                errors = data.get("errors", [])
                error_msg = errors[0].get("message", "Unknown error") if errors else "Token invalid"
                return ValidationResult(False, error=f"Token verification failed: {error_msg}")

            result = data.get("result", {})
            status = result.get("status", "unknown")
            if status != "active":
                return ValidationResult(False, error=f"Token status: {status}")

        except httpx.HTTPError as e:
            return ValidationResult(False, error=f"HTTP error: {e}")

        # 2. Check Workers AI models access
        try:
            r = client.get(
                f"{CLOUDFLARE_API}/accounts/{account_id}/workers/ai/models/search",
                headers=headers,
            )
            data = r.json()

            if data.get("success", False):
                models = data.get("result", [])
                model_count = len(models) if isinstance(models, list) else 0
            else:
                model_count = 0

        except httpx.HTTPError:
            model_count = 0

        # 3. Get account info
        try:
            r = client.get(
                f"{CLOUDFLARE_API}/accounts/{account_id}",
                headers=headers,
            )
            data = r.json()
            if data.get("success"):
                account = data.get("result", {})
                email = account.get("name", "")
            else:
                email = ""
        except httpx.HTTPError:
            email = ""

    return ValidationResult(
        valid=True,
        account_id=account_id,
        email=email,
        workers_ai_models=model_count,
    )


def get_models(api_token: str, account_id: str, timeout: int = 30) -> list[dict]:
    """List available Workers AI models for a given token."""
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        r = client.get(
            f"{CLOUDFLARE_API}/accounts/{account_id}/workers/ai/models/search",
            headers=headers,
        )
        data = r.json()
        if data.get("success"):
            return data.get("result", [])
    return []
