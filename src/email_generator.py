"""Temp email generator — creates disposable addresses via jackmail-compatible API."""

import httpx
from typing import Optional


class EmailGenerator:
    """Generate temporary email addresses via jackmail API."""

    def __init__(self, api_url: str, domains: list[str], timeout: int = 30):
        self.api_url = api_url
        self.domains = domains
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def create(self, username: Optional[str] = None, domain: Optional[str] = None) -> dict:
        """
        Create a new temporary email address.

        Args:
            username: Custom username. Auto-generated if None.
            domain: Email domain. Random from config if None.

        Returns:
            dict with 'email', 'jwt' (for checking inbox), 'address', 'domain'
        """
        if domain is None:
            import random
            domain = random.choice(self.domains)

        payload = {"domain": domain}
        if username:
            payload["name"] = username

        r = self.client.post(self.api_url, json=payload)
        r.raise_for_status()
        data = r.json()

        return {
            "email": data["address"],
            "jwt": data["jwt"],
            "address": data["address"],
            "domain": domain,
        }

    def check_inbox(self, jwt: str) -> list:
        """Check inbox for received emails."""
        # This depends on your mail API implementation
        base = self.api_url.replace("/new_address", "")
        r = self.client.get(f"{base}/parsed_mails", headers={"Authorization": f"Bearer {jwt}"})
        r.raise_for_status()
        return r.json()

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
