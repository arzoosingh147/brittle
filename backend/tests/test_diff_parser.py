import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from app.services.diff_parser import DiffParserService

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


class TestDiffParser(unittest.TestCase):
    def test_diff_parser_extracts_added_lines_and_valid_comment_targets(self):
        result = DiffParserService.parse_unified_diff(SAMPLE_DIFF)
        self.assertEqual(len(result.files), 1)
        file_diff = result.files[0]
        self.assertEqual(file_diff.target_file, "src/auth.ts")
        self.assertEqual(len(file_diff.added_lines), 2)
        self.assertIn(13, file_diff.valid_comment_lines)
        self.assertIn(14, file_diff.valid_comment_lines)
        self.assertEqual(result.total_added, 2)

    def test_diff_parser_filters_lockfiles_and_binaries(self):
        self.assertTrue(DiffParserService.should_ignore_file("package-lock.json"))
        self.assertTrue(DiffParserService.should_ignore_file("yarn.lock"))
        self.assertTrue(DiffParserService.should_ignore_file("app.min.js"))
        self.assertTrue(DiffParserService.should_ignore_file("logo.png"))
        self.assertFalse(DiffParserService.should_ignore_file("src/main.py"))


if __name__ == "__main__":
    unittest.main()
