import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from app.core.config import settings

# Ignored filenames, lockfiles, and file extensions
IGNORED_PATTERNS = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
    "Pipfile.lock",
    "composer.lock",
    "go.sum",
}

IGNORED_EXTENSIONS = {
    ".min.js",
    ".min.css",
    ".map",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".pdf",
    ".bin",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".zip",
    ".tar",
    ".gz",
}


@dataclass
class ChangedLine:
    line_number: int  # Line number in the new file (target)
    line_type: str    # '+' added, '-' removed, ' ' context
    content: str


@dataclass
class FileDiff:
    source_file: str
    target_file: str
    is_new: bool = False
    is_deleted: bool = False
    is_binary: bool = False
    hunks: List[str] = field(default_factory=list)
    added_lines: List[ChangedLine] = field(default_factory=list)
    valid_comment_lines: Set[int] = field(default_factory=set)  # Lines in the new file that can receive comments
    full_patch: str = ""

    @property
    def file_path(self) -> str:
        return self.target_file if not self.is_deleted else self.source_file


@dataclass
class ParsedDiffResult:
    files: List[FileDiff]
    total_added: int
    total_deleted: int
    ignored_files_count: int


class DiffParserService:
    """
    Parses unified git diffs, extracts line mappings for exact GitHub inline comments,
    and intelligently filters out lockfiles, binaries, and minified bundles.
    Built-in native parser with fallback to unidiff.
    """

    @staticmethod
    def should_ignore_file(file_path: str) -> bool:
        if not file_path or file_path == "/dev/null":
            return False

        filename = file_path.split("/")[-1].lower()
        if filename in IGNORED_PATTERNS:
            return True

        for ext in IGNORED_EXTENSIONS:
            if filename.endswith(ext):
                return True

        # Common test snapshots and build outputs
        if ".snap" in filename or "dist/" in file_path or "build/" in file_path or ".next/" in file_path:
            return True

        return False

    @classmethod
    def parse_unified_diff(cls, raw_diff_str: str) -> ParsedDiffResult:
        if not raw_diff_str or not raw_diff_str.strip():
            return ParsedDiffResult(files=[], total_added=0, total_deleted=0, ignored_files_count=0)

        # Try native parser first for resilient line counting, fall back to unidiff if needed
        try:
            return cls._parse_native(raw_diff_str)
        except Exception:
            try:
                import unidiff
                return cls._parse_with_unidiff(raw_diff_str)
            except Exception:
                return ParsedDiffResult(files=[], total_added=0, total_deleted=0, ignored_files_count=0)

    @classmethod
    def _parse_with_unidiff(cls, raw_diff_str: str) -> ParsedDiffResult:
        import unidiff
        patch_set = unidiff.PatchSet(raw_diff_str)
        file_diffs: List[FileDiff] = []
        total_added = 0
        total_deleted = 0
        ignored_count = 0

        for patched_file in patch_set:
            source_path = patched_file.source_file.lstrip("a/") if patched_file.source_file else ""
            target_path = patched_file.target_file.lstrip("b/") if patched_file.target_file else ""
            primary_path = target_path or source_path

            if cls.should_ignore_file(primary_path) or patched_file.is_binary_file:
                ignored_count += 1
                continue

            if len(file_diffs) >= settings.MAX_DIFF_FILES:
                break

            diff_obj = FileDiff(
                source_file=source_path,
                target_file=target_path,
                is_new=patched_file.is_added_file,
                is_deleted=patched_file.is_removed_file,
                is_binary=patched_file.is_binary_file,
                full_patch=str(patched_file),
            )

            file_lines_count = 0
            for hunk in patched_file:
                diff_obj.hunks.append(str(hunk))
                for line in hunk:
                    if file_lines_count >= settings.MAX_DIFF_LINES_PER_FILE:
                        break
                    if line.is_added:
                        total_added += 1
                        file_lines_count += 1
                        diff_obj.added_lines.append(
                            ChangedLine(line_number=line.target_line_no, line_type="+", content=line.value)
                        )
                        diff_obj.valid_comment_lines.add(line.target_line_no)
                    elif line.is_removed:
                        total_deleted += 1
                    elif line.is_context:
                        if line.target_line_no is not None:
                            diff_obj.valid_comment_lines.add(line.target_line_no)

            file_diffs.append(diff_obj)

        return ParsedDiffResult(
            files=file_diffs,
            total_added=total_added,
            total_deleted=total_deleted,
            ignored_files_count=ignored_count,
        )

    @classmethod
    def _parse_native(cls, raw_diff_str: str) -> ParsedDiffResult:
        """Native unified diff parser when unidiff is not installed or has strict hunk errors."""
        file_diffs: List[FileDiff] = []
        total_added = 0
        total_deleted = 0
        ignored_count = 0

        # Split diff into per-file blocks
        file_blocks = re.split(r"(?=^diff --git )", raw_diff_str, flags=re.MULTILINE)

        for block in file_blocks:
            if not block.strip():
                continue

            lines = block.splitlines()
            source_file = ""
            target_file = ""
            is_new = False
            is_deleted = False

            # Extract headers
            first_line = lines[0] if lines else ""
            git_match = re.search(r"diff --git a/(.*?) b/(.*)", first_line)
            if git_match:
                source_file = git_match.group(1)
                target_file = git_match.group(2)

            for line in lines[:10]:
                if line.startswith("--- a/"):
                    source_file = line[6:]
                elif line.startswith("--- /dev/null"):
                    is_new = True
                elif line.startswith("+++ b/"):
                    target_file = line[6:]
                elif line.startswith("+++ /dev/null"):
                    is_deleted = True

            primary_path = target_file or source_file
            if cls.should_ignore_file(primary_path):
                ignored_count += 1
                continue

            if len(file_diffs) >= settings.MAX_DIFF_FILES:
                break

            diff_obj = FileDiff(
                source_file=source_file,
                target_file=target_file,
                is_new=is_new,
                is_deleted=is_deleted,
                full_patch=block,
            )

            # Parse hunks
            hunk_header_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
            current_target_line = 0
            in_hunk = False

            for line in lines:
                hunk_match = hunk_header_re.match(line)
                if hunk_match:
                    in_hunk = True
                    current_target_line = int(hunk_match.group(3))
                    diff_obj.hunks.append(line)
                    continue

                if not in_hunk:
                    continue

                if line.startswith("+") and not line.startswith("+++"):
                    total_added += 1
                    diff_obj.added_lines.append(
                        ChangedLine(line_number=current_target_line, line_type="+", content=line[1:])
                    )
                    diff_obj.valid_comment_lines.add(current_target_line)
                    current_target_line += 1
                elif line.startswith("-") and not line.startswith("---"):
                    total_deleted += 1
                elif line.startswith(" ") or line == "":
                    diff_obj.valid_comment_lines.add(current_target_line)
                    current_target_line += 1

            file_diffs.append(diff_obj)

        return ParsedDiffResult(
            files=file_diffs,
            total_added=total_added,
            total_deleted=total_deleted,
            ignored_files_count=ignored_count,
        )

    @staticmethod
    def get_nearest_valid_comment_line(file_diff: FileDiff, target_line: int) -> int:
        if not file_diff.valid_comment_lines:
            return target_line
        if target_line in file_diff.valid_comment_lines:
            return target_line
        return min(file_diff.valid_comment_lines, key=lambda l: abs(l - target_line))
