import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from score_perplexity import parse_args


class TestParseArgs(unittest.TestCase):
    def test_requires_model(self):
        with self.assertRaises(SystemExit):
            parse_args([])

    def test_minimal_invocation(self):
        args = parse_args(["--model", "/fake/path.gguf"])
        self.assertEqual(args.model, Path("/fake/path.gguf"))
        self.assertEqual(args.format, "md")
        self.assertEqual(args.n_ctx, 8192)
        self.assertIsNone(args.n_threads)
        self.assertEqual(args.task, [])
        self.assertEqual(args.lang, [])
        self.assertIsNone(args.output)

    def test_filters_and_overrides(self):
        args = parse_args([
            "--model", "/m.gguf",
            "--format", "json",
            "--task", "json-parser",
            "--task", "http-rest",
            "--lang", "rust",
            "--n-threads", "4",
            "--n-ctx", "4096",
            "--output", "/tmp/out.json",
        ])
        self.assertEqual(args.format, "json")
        self.assertEqual(args.task, ["json-parser", "http-rest"])
        self.assertEqual(args.lang, ["rust"])
        self.assertEqual(args.n_threads, 4)
        self.assertEqual(args.n_ctx, 4096)
        self.assertEqual(args.output, Path("/tmp/out.json"))


if __name__ == "__main__":
    unittest.main()
