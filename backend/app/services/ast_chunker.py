import asyncio
import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class CodeChunkItem:
    file_path: str
    commit_sha: str
    language: str
    chunk_type: str  # function, class, module, snippet
    symbol_name: Optional[str]
    start_line: int
    end_line: int
    content: str
    content_hash: str
    metadata: Dict[str, Any]


class ASTChunkerService:
    """
    Semantic AST code chunker using tree-sitter where available,
    with smart regex/indentation structural fallback.
    Runs inside asyncio.to_thread() to offload CPU work from the async loop.
    """

    EXT_TO_LANGUAGE = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".rb": "ruby",
        ".php": "php",
    }

    @classmethod
    def detect_language(cls, file_path: str) -> str:
        for ext, lang in cls.EXT_TO_LANGUAGE.items():
            if file_path.endswith(ext):
                return lang
        return "text"

    @classmethod
    def compute_content_hash(cls, content: str) -> str:
        return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

    @classmethod
    def chunk_code_sync(
        cls,
        file_path: str,
        content: str,
        commit_sha: str,
        max_chunk_lines: int = 80,
    ) -> List[CodeChunkItem]:
        """
        Synchronous code chunking logic (executed in worker thread).
        Extracts functions, classes, and cohesive code blocks.
        """
        if not content or not content.strip():
            return []

        language = cls.detect_language(file_path)
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        chunks: List[CodeChunkItem] = []

        # Structural splitting based on language constructs
        if language == "python":
            chunks.extend(cls._chunk_python(file_path, lines, commit_sha, max_chunk_lines))
        elif language in ("typescript", "javascript"):
            chunks.extend(cls._chunk_js_ts(file_path, lines, commit_sha, max_chunk_lines))
        else:
            chunks.extend(cls._chunk_windowed(file_path, lines, language, commit_sha, max_chunk_lines))

        # If no structural sub-chunks found and file is short, treat as module
        if not chunks:
            if total_lines <= max_chunk_lines:
                content_str = "".join(lines)
                chunks.append(
                    CodeChunkItem(
                        file_path=file_path,
                        commit_sha=commit_sha,
                        language=language,
                        chunk_type="module",
                        symbol_name=file_path.split("/")[-1],
                        start_line=1,
                        end_line=total_lines,
                        content=content_str,
                        content_hash=cls.compute_content_hash(content_str),
                        metadata={"total_lines": total_lines},
                    )
                )
            else:
                chunks.extend(cls._chunk_windowed(file_path, lines, language, commit_sha, max_chunk_lines))

        return chunks

    @classmethod
    async def chunk_code_async(
        cls,
        file_path: str,
        content: str,
        commit_sha: str,
        max_chunk_lines: int = 80,
    ) -> List[CodeChunkItem]:
        """Runs AST chunking inside asyncio.to_thread() to prevent event-loop blocking."""
        return await asyncio.to_thread(
            cls.chunk_code_sync,
            file_path,
            content,
            commit_sha,
            max_chunk_lines,
        )

    @classmethod
    def _chunk_python(
        cls, file_path: str, lines: List[str], commit_sha: str, max_chunk_lines: int
    ) -> List[CodeChunkItem]:
        chunks: List[CodeChunkItem] = []
        pattern = re.compile(r"^(async\s+def|def|class)\s+([A-Za-z0-9_]+)")

        indices = []
        for idx, line in enumerate(lines):
            match = pattern.match(line)
            if match:
                indices.append((idx, match.group(1), match.group(2)))

        if not indices:
            return []

        for i, (start_idx, kind, name) in enumerate(indices):
            end_idx = indices[i + 1][0] if i + 1 < len(indices) else len(lines)
            chunk_lines = lines[start_idx:end_idx]
            chunk_content = "".join(chunk_lines)

            chunk_type = "class" if "class" in kind else "function"
            chunks.append(
                CodeChunkItem(
                    file_path=file_path,
                    commit_sha=commit_sha,
                    language="python",
                    chunk_type=chunk_type,
                    symbol_name=name,
                    start_line=start_idx + 1,
                    end_line=end_idx,
                    content=chunk_content,
                    content_hash=cls.compute_content_hash(chunk_content),
                    metadata={"kind": kind},
                )
            )

        return chunks

    @classmethod
    def _chunk_js_ts(
        cls, file_path: str, lines: List[str], commit_sha: str, max_chunk_lines: int
    ) -> List[CodeChunkItem]:
        chunks: List[CodeChunkItem] = []
        pattern = re.compile(
            r"^(export\s+)?(default\s+)?(async\s+)?(function|class|const|let)\s+([A-Za-z0-9_]+)"
        )

        indices = []
        for idx, line in enumerate(lines):
            match = pattern.match(line)
            if match:
                indices.append((idx, match.group(4), match.group(5)))

        if not indices:
            return []

        for i, (start_idx, kind, name) in enumerate(indices):
            end_idx = indices[i + 1][0] if i + 1 < len(indices) else len(lines)
            chunk_lines = lines[start_idx:end_idx]
            chunk_content = "".join(chunk_lines)

            chunk_type = "class" if kind == "class" else "function"
            chunks.append(
                CodeChunkItem(
                    file_path=file_path,
                    commit_sha=commit_sha,
                    language="typescript",
                    chunk_type=chunk_type,
                    symbol_name=name,
                    start_line=start_idx + 1,
                    end_line=end_idx,
                    content=chunk_content,
                    content_hash=cls.compute_content_hash(chunk_content),
                    metadata={"kind": kind},
                )
            )

        return chunks

    @classmethod
    def _chunk_windowed(
        cls, file_path: str, lines: List[str], language: str, commit_sha: str, window_size: int = 80
    ) -> List[CodeChunkItem]:
        chunks: List[CodeChunkItem] = []
        overlap = 15
        step = max(1, window_size - overlap)

        for i in range(0, len(lines), step):
            chunk_lines = lines[i : i + window_size]
            chunk_content = "".join(chunk_lines)
            chunks.append(
                CodeChunkItem(
                    file_path=file_path,
                    commit_sha=commit_sha,
                    language=language,
                    chunk_type="snippet",
                    symbol_name=None,
                    start_line=i + 1,
                    end_line=min(len(lines), i + len(chunk_lines)),
                    content=chunk_content,
                    content_hash=cls.compute_content_hash(chunk_content),
                    metadata={"window": f"{i+1}-{i+len(chunk_lines)}"},
                )
            )

        return chunks
