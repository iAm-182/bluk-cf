"""Tests for token validation."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.token_validator import validate_token, get_models


class TestTokenValidator:
    """Test token validation against Cloudflare API."""

    def test_invalid_token_returns_invalid(self):
        """A fake token should return invalid."""
        result = validate_token("cfut_invalidtoken123", "fakeaccountid123")
        assert result.valid is False
        assert result.error != ""

    def test_validation_result_structure(self):
        """ValidationResult should have all expected fields."""
        result = validate_token("cfut_fake", "fakeid")
        d = result.to_dict()
        assert "token_valid" in d
        assert "workers_ai_models" in d
        assert "validation_error" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
