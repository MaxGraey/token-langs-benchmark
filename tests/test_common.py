import unittest
from pathlib import Path

from scripts._common import (
    LANGUAGES, TASKS, Language, language_for, path_for, scan_sources,
    load_prompt, render_prompt, prompt_sha256,
)

REPO = Path(__file__).resolve().parent.parent


class TestRegistries(unittest.TestCase):
    def test_languages_have_unique_slugs(self):
        slugs = [l.slug for l in LANGUAGES]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_languages_have_unique_src_dirs(self):
        dirs = [l.src_dir for l in LANGUAGES]
        self.assertEqual(len(dirs), len(set(dirs)))

    def test_baseline_languages_present(self):
        """Intentional pin on the current registry contents.

        When adding a new language, update this set deliberately - the
        failure is the reminder that you touched the canonical baseline.
        """
        slugs = {l.slug for l in LANGUAGES}
        self.assertEqual(slugs, {"rust", "typescript", "zig", "go", "python"})

    def test_baseline_tasks_present(self):
        """Intentional pin on the current task set; update when adding tasks."""
        self.assertEqual(
            set(TASKS),
            {"find-prime-numbers", "http-rest", "json-parser", "word-frequency"},
        )

    def test_language_for_returns_registered(self):
        lang = language_for("rust")
        self.assertEqual(lang.slug, "rust")
        self.assertEqual(lang.display, "Rust")
        self.assertEqual(lang.prompt_label, "Rust")

    def test_display_falls_back_to_prompt_label_when_short_unset(self):
        # rust and zig have no `short`, so display == prompt_label
        self.assertEqual(language_for("rust").display, "Rust")
        self.assertEqual(language_for("zig").display, "Zig")
        # typescript has short="TS"
        self.assertEqual(language_for("typescript").display, "TS")
        self.assertEqual(language_for("typescript").prompt_label, "TypeScript")

    def test_language_for_unknown_raises(self):
        with self.assertRaises(KeyError):
            language_for("cobol")

    def test_path_for_snake_case_lang(self):
        rust = language_for("rust")
        path = path_for(REPO, "find-prime-numbers", rust)
        self.assertEqual(path, REPO / "rust/src/bin/find_prime_numbers.rs")

    def test_path_for_kebab_case_lang(self):
        ts = language_for("typescript")
        path = path_for(REPO, "find-prime-numbers", ts)
        self.assertEqual(path, REPO / "typescript/src/find-prime-numbers.ts")

    def test_path_for_with_file_stem(self):
        """Go uses cmd/<task>/main.go: file_stem forces per-task subdir."""
        go = language_for("go")
        path = path_for(REPO, "find-prime-numbers", go)
        self.assertEqual(path, REPO / "go/cmd/find_prime_numbers/main.go")


class TestScanSources(unittest.TestCase):
    def test_returns_one_entry_per_language(self):
        result = scan_sources(REPO)
        self.assertEqual(set(result.keys()), {l.slug for l in LANGUAGES})

    def test_returns_one_file_per_task_per_language(self):
        result = scan_sources(REPO)
        for slug, files in result.items():
            self.assertEqual(set(files.keys()), set(TASKS), f"{slug}: {files}")

    def test_file_paths_exist(self):
        result = scan_sources(REPO)
        for slug, files in result.items():
            for path in files.values():
                self.assertTrue(path.exists(), f"missing: {path}")


class TestPromptLoader(unittest.TestCase):
    def test_load_prompt_returns_template_string(self):
        text = load_prompt(REPO, "find-prime-numbers")
        self.assertIn("{lang}", text)

    def test_load_prompt_missing_task_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_prompt(REPO, "no-such-task")

    def test_render_prompt_substitutes_lang_and_appends_separator(self):
        rendered = render_prompt(REPO, "find-prime-numbers", "Rust")
        self.assertIn("Rust", rendered)
        self.assertNotIn("{lang}", rendered)
        self.assertTrue(rendered.endswith("\n\n"), "must end with the \\n\\n separator")

    def test_prompt_sha256_is_stable(self):
        a = prompt_sha256(render_prompt(REPO, "find-prime-numbers", "Rust"))
        b = prompt_sha256(render_prompt(REPO, "find-prime-numbers", "Rust"))
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in a))

    def test_prompt_sha256_differs_per_lang(self):
        rust_sha = prompt_sha256(render_prompt(REPO, "find-prime-numbers", "Rust"))
        ts_sha   = prompt_sha256(render_prompt(REPO, "find-prime-numbers", "TypeScript"))
        self.assertNotEqual(rust_sha, ts_sha)
