import sys
import unittest
import hmac
import hashlib
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.diff_parser import DiffParserService
from app.services.ast_chunker import ASTChunkerService
from app.agents.schemas import InlineCommentOutput, SpecialistReviewOutput, AggregatedReviewOutput
from app.core.security import verify_github_signature, create_access_token, decode_access_token
from app.core.config import settings

SAMPLE_DIFF = """diff --git a/src/auth.ts b/src/auth.ts
index 1234567..89abcdef 100644
--- a/src/auth.ts
+++ b/src/auth.ts
@@ -10,6 +10,8 @@ export async function verifyToken(token: string) {
     if (!token) return null;
     const decoded = jwt.decode(token);
+    // Vulnerability: No signature verification
+    const user = await db.getUser(decoded.sub);
     return user;
 }
"""

SAMPLE_PY = """
class UserService:
    def __init__(self, db):
        self.db = db

    async def get_user_by_id(self, user_id: int):
        return await self.db.find(user_id)

def calculate_metric(a: int, b: int) -> int:
    return a * b + 42
"""


class TestBrittleBackend(unittest.TestCase):
    def test_diff_parser_lines_and_valid_comment_targets(self):
        result = DiffParserService.parse_unified_diff(SAMPLE_DIFF)
        self.assertEqual(len(result.files), 1)
        file_diff = result.files[0]
        self.assertEqual(file_diff.target_file, "src/auth.ts")
        self.assertEqual(len(file_diff.added_lines), 2)
        self.assertIn(13, file_diff.valid_comment_lines)
        self.assertIn(14, file_diff.valid_comment_lines)
        self.assertEqual(result.total_added, 2)

    def test_diff_parser_filters_lockfiles(self):
        self.assertTrue(DiffParserService.should_ignore_file("package-lock.json"))
        self.assertTrue(DiffParserService.should_ignore_file("yarn.lock"))
        self.assertTrue(DiffParserService.should_ignore_file("app.min.js"))
        self.assertTrue(DiffParserService.should_ignore_file("logo.png"))
        self.assertFalse(DiffParserService.should_ignore_file("src/main.py"))

    def test_ast_chunker(self):
        chunks = ASTChunkerService.chunk_code_sync("app/service.py", SAMPLE_PY, "commit123")
        self.assertGreaterEqual(len(chunks), 2)
        symbols = {c.symbol_name for c in chunks if c.symbol_name}
        self.assertTrue("UserService" in symbols or "calculate_metric" in symbols)
        for chunk in chunks:
            self.assertTrue(chunk.content_hash)
            self.assertEqual(chunk.commit_sha, "commit123")
            self.assertEqual(chunk.language, "python")

    def test_pydantic_agent_schemas(self):
        comment = InlineCommentOutput(
            file_path="src/auth.ts",
            line_number=13,
            side="RIGHT",
            severity="HIGH",
            title="Unverified JWT Decode",
            comment="Token is decoded without signature validation.",
            suggestion="jwt.verify(token, secret)",
        )
        self.assertEqual(comment.severity, "HIGH")

        spec = SpecialistReviewOutput(
            agent_name="security",
            summary="Security issues detected",
            risk_score=7,
            findings=[comment],
        )
        self.assertEqual(spec.risk_score, 7)
        self.assertEqual(len(spec.findings), 1)

        agg = AggregatedReviewOutput(
            summary="Review finished with changes requested",
            risk_score=7,
            recommendation="REQUEST_CHANGES",
            comments=[comment],
            security_issues_count=1,
            perf_issues_count=0,
            quality_issues_count=0,
        )
        self.assertEqual(agg.recommendation, "REQUEST_CHANGES")

    def test_github_webhook_hmac_signature(self):
        payload = b'{"action": "opened", "number": 1}'
        mac = hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256,
        )
        valid_header = f"sha256={mac.hexdigest()}"
        self.assertTrue(verify_github_signature(payload, valid_header))
        self.assertFalse(verify_github_signature(payload, "sha256=invalidhash123"))
        self.assertFalse(verify_github_signature(payload, None))

    def test_jwt_tokens(self):
        payload = {"sub": "user_123", "role": "admin"}
        token = create_access_token(payload, expires_delta=3600)
        decoded = decode_access_token(token)
        self.assertEqual(decoded["sub"], "user_123")
        self.assertEqual(decoded["role"], "admin")


if __name__ == "__main__":
    unittest.main()
