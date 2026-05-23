import math
import sys
import unittest
from pathlib import Path
from typing import List
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from score_perplexity import (
    Result,
    detect_physical_cores,
    parse_args,
    pick_winner,
    score_one,
    to_csv,
    to_json,
    to_markdown,
)


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


class FakeScorer:
    """In-memory scorer for tests.

    tokenize_map: dict mapping (text, add_bos) -> token id list
    scores_seq: list of logit vectors, indexed by absolute position
    """
    def __init__(self, tokenize_map, scores_seq, vocab_size=8):
        self._tokenize_map = tokenize_map
        self.vocab_size = vocab_size
        self.scores = np.array(scores_seq, dtype=np.float32)
        self.prefill_called_with = None

    def tokenize(self, text: str, add_bos: bool) -> List[int]:
        return list(self._tokenize_map[(text, add_bos)])

    def prefill(self, tokens: List[int]) -> None:
        self.prefill_called_with = list(tokens)


class TestScoreOne(unittest.TestCase):

    def _uniform_logits(self, vocab=8):
        return [0.0] * vocab

    def test_uniform_distribution_gives_log2_vocab_per_token(self):
        # Prompt -> [10, 11], code -> [3, 4, 5]. Uniform logits over vocab=8.
        # Expected: 3 scored tokens, each contributing log2(8) = 3 bits.
        prompt = "prompt-text\n\n"
        code = "code-text"
        full_len = 5
        fake = FakeScorer(
            tokenize_map={
                (prompt, True): [10, 11],
                (code, False): [3, 4, 5],
            },
            scores_seq=[self._uniform_logits() for _ in range(full_len)],
            vocab_size=8,
        )
        tokens_scored, total_bits = score_one(fake, prompt, code)
        self.assertEqual(tokens_scored, 3)
        self.assertAlmostEqual(total_bits, 3 * math.log2(8), places=5)

    def test_index_offset_uses_scores_minus_one(self):
        # Hand-built logits where scores[1] strongly prefers token id 3
        # (the first scored code token), scores[2] prefers id 4, scores[3] id 5.
        # If the implementer uses scores[i] instead of scores[i-1], bits blow up.
        prompt = "p\n\n"
        code = "c"
        # full_tokens = [10, 11, 3, 4, 5], len(prompt_tokens) = 2
        # Scoring positions i=2,3,4 read scores[1], scores[2], scores[3].
        vocab = 8
        def peak_at(idx):
            v = [-10.0] * vocab
            v[idx] = 0.0
            return v
        scores_seq = [
            peak_at(0),  # scores[0] - unused
            peak_at(3),  # scores[1] - predicts token at position 2 (id 3)
            peak_at(4),  # scores[2] - predicts token at position 3 (id 4)
            peak_at(5),  # scores[3] - predicts token at position 4 (id 5)
            peak_at(0),  # scores[4] - unused
        ]
        fake = FakeScorer(
            tokenize_map={(prompt, True): [10, 11], (code, False): [3, 4, 5]},
            scores_seq=scores_seq,
            vocab_size=vocab,
        )
        tokens_scored, total_bits = score_one(fake, prompt, code)
        self.assertEqual(tokens_scored, 3)
        # Each predicted token has near-1.0 probability under its softmax,
        # so total_bits should be very close to 0.
        self.assertLess(total_bits, 0.1, f"got {total_bits}, expected near zero")

    def test_prefill_receives_id_concatenated_full_tokens(self):
        prompt = "p\n\n"
        code = "c"
        fake = FakeScorer(
            tokenize_map={(prompt, True): [10, 11], (code, False): [3, 4, 5]},
            scores_seq=[self._uniform_logits() for _ in range(5)],
        )
        score_one(fake, prompt, code)
        self.assertEqual(fake.prefill_called_with, [10, 11, 3, 4, 5])

    def test_bos_in_prompt_not_scored(self):
        # The first prompt token (BOS) sits at position 0 and is never
        # scored. We assert that by changing the BOS id to something
        # outrageous and confirming total_bits is unchanged.
        prompt = "p\n\n"
        code = "c"
        scores_seq = [self._uniform_logits() for _ in range(5)]
        fake_a = FakeScorer(
            tokenize_map={(prompt, True): [1, 11], (code, False): [3, 4, 5]},
            scores_seq=scores_seq,
        )
        fake_b = FakeScorer(
            tokenize_map={(prompt, True): [9999, 11], (code, False): [3, 4, 5]},
            scores_seq=scores_seq,
        )
        _, bits_a = score_one(fake_a, prompt, code)
        _, bits_b = score_one(fake_b, prompt, code)
        self.assertEqual(bits_a, bits_b)

    def test_empty_code_yields_zero_bits(self):
        prompt = "p\n\n"
        fake = FakeScorer(
            tokenize_map={(prompt, True): [10, 11], ("", False): []},
            scores_seq=[self._uniform_logits() for _ in range(2)],
        )
        tokens_scored, total_bits = score_one(fake, prompt, "")
        self.assertEqual(tokens_scored, 0)
        self.assertEqual(total_bits, 0.0)


def _result(lang, tokens, byte_len, total_bits, prompt_sha="x", task="t"):
    avg_nll = total_bits / tokens if tokens else 0.0
    bpb = total_bits / byte_len if byte_len else 0.0
    return Result(task=task, lang=lang, tokens=tokens, byte_len=byte_len,
                  total_bits=total_bits, bpb=bpb, avg_nll=avg_nll,
                  ppl=2 ** avg_nll if tokens else 0.0,
                  prompt_sha256=prompt_sha)


class TestPickWinner(unittest.TestCase):
    def test_strict_winner_by_total_bits(self):
        rows = [
            _result("rust",       100, 400, 500.0),
            _result("typescript", 80,  300, 400.0),
            _result("zig",        120, 500, 600.0),
        ]
        self.assertEqual(pick_winner(rows), "typescript")

    def test_tie_broken_by_fewer_tokens(self):
        rows = [
            _result("rust",       100, 400, 400.0),
            _result("typescript", 80,  300, 400.0),
        ]
        self.assertEqual(pick_winner(rows), "typescript")

    def test_tie_broken_alphabetically_when_all_else_equal(self):
        rows = [
            _result("typescript", 100, 400, 400.0),
            _result("rust",       100, 400, 400.0),
        ]
        self.assertEqual(pick_winner(rows), "rust")


class TestOutputWriters(unittest.TestCase):
    def _sample(self):
        return [
            _result("rust",       100, 400, 500.0, prompt_sha="aa", task="t1"),
            _result("typescript", 80,  300, 400.0, prompt_sha="bb", task="t1"),
            _result("zig",        120, 500, 600.0, prompt_sha="cc", task="t1"),
        ]

    def test_markdown_has_header_winner_and_aggregate(self):
        md = to_markdown(self._sample())
        self.assertIn("| Example", md)
        self.assertIn("Winner", md)
        self.assertIn("Rust bits", md)
        self.assertIn("Rust bpb", md)
        self.assertIn("typescript", md)
        self.assertIn("Aggregate bpb", md)

    def test_json_has_meta_and_rows_with_bpb_and_byte_len(self):
        meta = {
            "model": "fake",
            "model_path_sha256": "abc",
            "n_ctx": 8192,
            "scored_at": "2026-05-23T00:00:00Z",
        }
        out = to_json(self._sample(), meta)
        import json
        parsed = json.loads(out)
        self.assertEqual(parsed["model"], "fake")
        self.assertEqual(parsed["model_path_sha256"], "abc")
        self.assertEqual(len(parsed["results"]), 3)
        row = parsed["results"][0]
        for field in ("prompt_sha256", "byte_len", "bpb", "total_bits", "tokens"):
            self.assertIn(field, row)

    def test_csv_has_header_and_three_rows(self):
        text = to_csv(self._sample())
        lines = text.strip().splitlines()
        self.assertEqual(len(lines), 4)  # header + 3 rows
        self.assertTrue(lines[0].startswith("task,lang,tokens,byte_len,total_bits,bpb,"))


class TestDetectPhysicalCores(unittest.TestCase):
    def test_macos_uses_sysctl_perflevel0(self):
        # Apple Silicon: hw.perflevel0.physicalcpu returns P-core count.
        with mock.patch("score_perplexity.platform") as plat, \
             mock.patch("score_perplexity.subprocess") as sp:
            plat.system.return_value = "Darwin"
            sp.check_output.return_value = "6\n"
            self.assertEqual(detect_physical_cores(), 6)
            sp.check_output.assert_called_with(
                ["sysctl", "-n", "hw.perflevel0.physicalcpu"], text=True
            )

    def test_macos_falls_back_to_physicalcpu_when_perflevel0_missing(self):
        with mock.patch("score_perplexity.platform") as plat, \
             mock.patch("score_perplexity.subprocess") as sp:
            plat.system.return_value = "Darwin"
            sp.CalledProcessError = Exception
            sp.check_output.side_effect = [Exception("no perflevel0"), "4\n"]
            self.assertEqual(detect_physical_cores(), 4)
            self.assertEqual(sp.check_output.call_count, 2)

    def test_linux_intel_halves_logical_count(self):
        with mock.patch("score_perplexity.platform") as plat, \
             mock.patch("score_perplexity.os") as os_mock:
            plat.system.return_value = "Linux"
            plat.machine.return_value = "x86_64"
            os_mock.cpu_count.return_value = 12
            self.assertEqual(detect_physical_cores(), 6)

    def test_linux_arm_uses_full_count(self):
        with mock.patch("score_perplexity.platform") as plat, \
             mock.patch("score_perplexity.os") as os_mock:
            plat.system.return_value = "Linux"
            plat.machine.return_value = "aarch64"
            os_mock.cpu_count.return_value = 8
            self.assertEqual(detect_physical_cores(), 8)


if __name__ == "__main__":
    unittest.main()
