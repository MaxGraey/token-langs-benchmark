import math
import sys
import unittest
from pathlib import Path
from typing import List

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from score_perplexity import parse_args, score_one


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


if __name__ == "__main__":
    unittest.main()
