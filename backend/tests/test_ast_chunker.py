import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from app.services.ast_chunker import ASTChunkerService

SAMPLE_PY = """
class UserService:
    def __init__(self, db):
        self.db = db

    async def get_user_by_id(self, user_id: int):
        return await self.db.find(user_id)

def calculate_metric(a: int, b: int) -> int:
    return a * b + 42
"""


class TestASTChunker(unittest.TestCase):
    def test_ast_chunker_extracts_functions_and_classes(self):
        chunks = ASTChunkerService.chunk_code_sync("app/service.py", SAMPLE_PY, "commit123")
        self.assertGreaterEqual(len(chunks), 2)
        symbols = {c.symbol_name for c in chunks if c.symbol_name}
        self.assertTrue("UserService" in symbols or "calculate_metric" in symbols)
        for chunk in chunks:
            self.assertTrue(chunk.content_hash)
            self.assertEqual(chunk.commit_sha, "commit123")
            self.assertEqual(chunk.language, "python")


if __name__ == "__main__":
    unittest.main()
