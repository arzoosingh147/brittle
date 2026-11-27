import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
import hmac
import hashlib
import json
from app.core.config import settings
from app.core.security import verify_github_signature


class TestWebhooks(unittest.TestCase):
    def test_verify_github_signature_valid(self):
        payload = json.dumps({"hook_id": 9999}).encode("utf-8")
        mac = hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256,
        )
        sig = f"sha256={mac.hexdigest()}"
        self.assertTrue(verify_github_signature(payload, sig))

    def test_verify_github_signature_invalid(self):
        payload = b'{"data": "test"}'
        self.assertFalse(verify_github_signature(payload, "sha256=invalid"))
        self.assertFalse(verify_github_signature(payload, None))


if __name__ == "__main__":
    unittest.main()
