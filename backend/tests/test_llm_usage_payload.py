import unittest

from app.core.llm_usage import build_usage_payload


class LLMUsagePayloadTests(unittest.TestCase):
    def test_uses_callback_tokens_when_available_and_reads_model_from_response_metadata(self) -> None:
        callback_usage = {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        }
        raw_message = {
            "response_metadata": {
                "model_provider": "openai",
                "model_name": "minimax/minimax-m2.5-20260211",
                "token_usage": {
                    "prompt_tokens": 40,
                    "completion_tokens": 50,
                    "total_tokens": 90,
                },
            }
        }

        usage = build_usage_payload(
            callback_usage_metadata=callback_usage,
            raw_message=raw_message,
            fallback_provider="openai-compatible",
            fallback_model="minimax/minimax-m2.5",
        )

        self.assertEqual(usage["input_tokens"], 10)
        self.assertEqual(usage["output_tokens"], 20)
        self.assertEqual(usage["total_tokens"], 30)
        self.assertEqual(usage["model_provider"], "openai")
        self.assertEqual(usage["model_name"], "minimax/minimax-m2.5-20260211")

    def test_falls_back_to_raw_tokens_and_configured_model(self) -> None:
        callback_usage = {}
        raw_message = {
            "response_metadata": {
                "token_usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 34,
                    "total_tokens": 46,
                }
            }
        }

        usage = build_usage_payload(
            callback_usage_metadata=callback_usage,
            raw_message=raw_message,
            fallback_provider="openai-compatible",
            fallback_model="minimax/minimax-m2.5",
        )

        self.assertEqual(usage["input_tokens"], 12)
        self.assertEqual(usage["output_tokens"], 34)
        self.assertEqual(usage["total_tokens"], 46)
        self.assertEqual(usage["model_provider"], "openai-compatible")
        self.assertEqual(usage["model_name"], "minimax/minimax-m2.5")


if __name__ == "__main__":
    unittest.main()
