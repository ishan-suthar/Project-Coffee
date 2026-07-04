import json
import unittest
from unittest import mock

from roastery.openrouter_client import OpenRouterResult, run_order


class FakeResponse:
    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self._body


class OpenRouterClientTests(unittest.TestCase):
    def test_run_order_returns_error_when_api_key_is_missing(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            result = run_order("test/model", "Say OK")

        self.assertIsInstance(result, OpenRouterResult)
        self.assertEqual(result.model, "test/model")
        self.assertEqual(result.response_text, "")
        self.assertIsNone(result.latency_seconds)
        self.assertIsNone(result.usage)
        self.assertEqual(result.errors, ["OPENROUTER_API_KEY is not set."])

    def test_run_order_parses_successful_response(self):
        body = json.dumps(
            {
                "choices": [{"message": {"content": "OK"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
            }
        ).encode("utf-8")

        with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": "dummy-key"}, clear=True):
            with mock.patch(
                "roastery.openrouter_client.request.urlopen",
                return_value=FakeResponse(body),
            ):
                result = run_order("test/model", "Say OK")

        self.assertEqual(result.model, "test/model")
        self.assertEqual(result.response_text, "OK")
        self.assertIsNotNone(result.latency_seconds)
        self.assertEqual(result.usage["total_tokens"], 4)
        self.assertEqual(result.errors, [])


if __name__ == "__main__":
    unittest.main()
