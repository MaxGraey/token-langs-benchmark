from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Literal, Optional, Tuple


FileCase = Literal["snake", "kebab"]


@dataclass(frozen=True)
class Language:
    """All per-language knobs. Add a new language by appending to LANGUAGES."""
    slug: str            # internal key, lowercase: "rust"
    prompt_label: str    # name used in {lang} substitution: "Rust", "TypeScript", "Go"
    src_dir: str         # source root relative to repo: "rust/src/bin"
    file_ext: str        # ".rs"
    file_case: FileCase  # task-slug to filename rule; type-checker validates
    short: Optional[str] = None  # narrow markdown column header; default = prompt_label
    file_stem: Optional[str] = None  # when set, path is <src_dir>/<task>/<file_stem><ext>
                                     # used by Go for cmd/<task>/main.go layout

    @property
    def display(self) -> str:
        """Header used in the markdown table; falls back to prompt_label."""
        return self.short or self.prompt_label


LANGUAGES: Tuple[Language, ...] = (
    Language("rust",       "Rust",       "rust/src/bin",   ".rs",  "snake"),
    Language("typescript", "TypeScript", "typescript/src", ".ts",  "kebab", short="TS"),
    Language("zig",        "Zig",        "zig/src",        ".zig", "snake"),
    Language("go",         "Go",         "go/cmd",         ".go",  "snake", file_stem="main"),
    Language("python",     "Python",     "python/src",     ".py",  "snake", short="Py"),
)


TASKS: Tuple[str, ...] = (
    "find-prime-numbers",
    "http-rest",
    "json-parser",
    "word-frequency",
)


_LANGS_BY_SLUG: Dict[str, Language] = {l.slug: l for l in LANGUAGES}


def language_for(slug: str) -> Language:
    if slug not in _LANGS_BY_SLUG:
        raise KeyError(f"unknown language slug: {slug!r}; known: {list(_LANGS_BY_SLUG)}")
    return _LANGS_BY_SLUG[slug]


def _task_to_filename(task: str, case: FileCase) -> str:
    if case == "snake":
        return task.replace("-", "_")
    if case == "kebab":
        return task
    raise ValueError(f"unknown file_case: {case!r}")  # unreachable under Literal


def path_for(repo_root: Path, task: str, lang: Language) -> Path:
    """Derive the source-file path for one (task, lang) pair from the registry."""
    name = _task_to_filename(task, lang.file_case)
    if lang.file_stem is not None:
        return repo_root / lang.src_dir / name / f"{lang.file_stem}{lang.file_ext}"
    return repo_root / lang.src_dir / f"{name}{lang.file_ext}"


def scan_sources(repo_root: Path) -> Dict[str, Dict[str, Path]]:
    """Return {lang_slug: {task: absolute_path}} derived from LANGUAGES x TASKS."""
    return {
        lang.slug: {task: path_for(repo_root, task, lang) for task in TASKS}
        for lang in LANGUAGES
    }
