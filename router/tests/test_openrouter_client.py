import unittest

import httpx

from router.app.openrouter_client import (
    OpenRouterClientError,
    StreamChunk,
    _http_error_message,
    _parse_sse_line,
    stream_order,
)


def _sse_body(*data_lines: str) -> bytes:
    frames = [f"data: {line}\n\n" for line in data_lines]
    return "".join(frames).encode("utf-8")


def _mock_client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


class ParseSseLineTests(unittest.TestCase):
    def test_ignores_blank_lines(self):
        self.assertIsNone(_parse_sse_line(""))
        self.assertIsNone(_parse_sse_line("   "))

    def test_ignores_non_data_lines(self):
        self.assertIsNone(_parse_sse_line(": comment"))

    def test_done_sentinel(self):
        chunk = _parse_sse_line("data: [DONE]")
        self.assertTrue(chunk.is_final)

    def test_parses_content_delta(self):
        chunk = _parse_sse_line('data: {"choices": [{"delta": {"content": "Hi"}}]}')
        self.assertEqual(chunk.content_delta, "Hi")
        self.assertIsNone(chunk.finish_reason)

    def test_parses_usage(self):
        chunk = _parse_sse_line(
            'data: {"choices": [{"delta": {}, "finish_reason": "stop"}], '
            '"usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8}}'
        )
        self.assertEqual(chunk.finish_reason, "stop")
        self.assertEqual(chunk.usage["total_tokens"], 8)

    def test_malformed_json_returns_none(self):
        self.assertIsNone(_parse_sse_line("data: {not valid json"))


class HttpErrorMessageTests(unittest.TestCase):
    def test_structured_error_body(self):
        body = b'{"error": {"message": "rate limited"}}'
        message = _http_error_message(429, body)
        self.assertIn("429", message)
        self.assertIn("rate limited", message)

    def test_unstructured_error_body(self):
        message = _http_error_message(500, b"internal error")
        self.assertIn("500", message)
        self.assertIn("internal error", message)

    def test_empty_body(self):
        message = _http_error_message(503, b"")
        self.assertIn("503", message)


class StreamOrderTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_api_key_raises(self):
        async def handler(request):
            raise AssertionError("no request should be made when the key is missing")

        client = _mock_client(handler)
        with self.assertRaises(OpenRouterClientError):
            async for _ in stream_order("vendor/model:free", "hi", api_key="", http_client=client):
                pass
        await client.aclose()

    async def test_successful_stream_yields_chunks_and_final(self):
        body = _sse_body(
            '{"choices": [{"delta": {"content": "Hel"}}]}',
            '{"choices": [{"delta": {"content": "lo"}}]}',
            '{"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"total_tokens": 12}}',
            "[DONE]",
        )

        async def handler(request):
            self.assertEqual(request.headers["Authorization"], "Bearer dummy-key")
            return httpx.Response(200, content=body)

        client = _mock_client(handler)
        chunks = [
            chunk
            async for chunk in stream_order(
                "vendor/model:free", "hi", api_key="dummy-key", http_client=client
            )
        ]
        await client.aclose()

        content = "".join(c.content_delta for c in chunks if not c.is_final)
        self.assertEqual(content, "Hello")
        self.assertTrue(chunks[-1].is_final)
        usage_chunk = next(c for c in chunks if c.usage is not None)
        self.assertEqual(usage_chunk.usage["total_tokens"], 12)

    async def test_http_error_raises_openrouter_client_error(self):
        async def handler(request):
            return httpx.Response(429, content=b'{"error": {"message": "rate limited"}}')

        client = _mock_client(handler)
        with self.assertRaises(OpenRouterClientError) as ctx:
            async for _ in stream_order(
                "vendor/model:free", "hi", api_key="dummy-key", http_client=client
            ):
                pass
        await client.aclose()
        self.assertIn("rate limited", str(ctx.exception))

    async def test_never_sends_api_key_in_body(self):
        seen_bodies = []

        async def handler(request):
            seen_bodies.append(request.content)
            return httpx.Response(200, content=_sse_body("[DONE]"))

        client = _mock_client(handler)
        async for _ in stream_order(
            "vendor/model:free", "hi", api_key="super-secret-key", http_client=client
        ):
            pass
        await client.aclose()

        for body in seen_bodies:
            self.assertNotIn(b"super-secret-key", body)

    async def test_no_images_sends_plain_string_content(self):
        """Backward compatibility: every non-image request (and every call
        before Brew 38) must keep sending content as a plain string, not
        the multimodal array form."""

        import json as json_module

        seen_bodies = []

        async def handler(request):
            seen_bodies.append(request.content)
            return httpx.Response(200, content=_sse_body("[DONE]"))

        client = _mock_client(handler)
        async for _ in stream_order("vendor/model:free", "hi", api_key="k", http_client=client):
            pass
        await client.aclose()

        payload = json_module.loads(seen_bodies[0])
        self.assertEqual(payload["messages"][0]["content"], "hi")

    async def test_images_send_multimodal_content_array(self):
        import json as json_module

        seen_bodies = []

        async def handler(request):
            seen_bodies.append(request.content)
            return httpx.Response(200, content=_sse_body("[DONE]"))

        client = _mock_client(handler)
        data_url = "data:image/png;base64,iVBORw0KGgo="
        async for _ in stream_order(
            "vendor/vision-model:free",
            "What is in this image?",
            api_key="k",
            http_client=client,
            image_data_urls=[data_url],
        ):
            pass
        await client.aclose()

        payload = json_module.loads(seen_bodies[0])
        content = payload["messages"][0]["content"]
        self.assertIsInstance(content, list)
        self.assertEqual(content[0], {"type": "text", "text": "What is in this image?"})
        self.assertEqual(content[1], {"type": "image_url", "image_url": {"url": data_url}})

    async def test_multiple_images_all_included(self):
        import json as json_module

        seen_bodies = []

        async def handler(request):
            seen_bodies.append(request.content)
            return httpx.Response(200, content=_sse_body("[DONE]"))

        client = _mock_client(handler)
        urls = ["data:image/png;base64,AAA=", "data:image/jpeg;base64,BBB="]
        async for _ in stream_order(
            "vendor/vision-model:free", "compare these", api_key="k", http_client=client, image_data_urls=urls
        ):
            pass
        await client.aclose()

        payload = json_module.loads(seen_bodies[0])
        content = payload["messages"][0]["content"]
        self.assertEqual(len(content), 3)  # 1 text part + 2 image parts

    async def test_no_history_messages_sends_byte_for_byte_the_same_single_message_payload(self):
        """Brew 46 (docs/design/conversation-memory-design.md): the
        remember_chat=False path must be indistinguishable from every
        call before this Brew existed."""

        import json as json_module

        seen_bodies = []

        async def handler(request):
            seen_bodies.append(request.content)
            return httpx.Response(200, content=_sse_body("[DONE]"))

        client = _mock_client(handler)
        async for _ in stream_order("vendor/model:free", "hi", api_key="k", http_client=client):
            pass
        await client.aclose()

        payload = json_module.loads(seen_bodies[0])
        self.assertEqual(payload["messages"], [{"role": "user", "content": "hi"}])

    async def test_history_messages_are_prepended_oldest_first(self):
        import json as json_module

        seen_bodies = []

        async def handler(request):
            seen_bodies.append(request.content)
            return httpx.Response(200, content=_sse_body("[DONE]"))

        client = _mock_client(handler)
        history = [
            {"role": "user", "content": "earlier question"},
            {"role": "assistant", "content": "earlier answer"},
        ]
        async for _ in stream_order(
            "vendor/model:free", "follow-up", api_key="k", http_client=client, history_messages=history
        ):
            pass
        await client.aclose()

        payload = json_module.loads(seen_bodies[0])
        self.assertEqual(
            payload["messages"],
            [
                {"role": "user", "content": "earlier question"},
                {"role": "assistant", "content": "earlier answer"},
                {"role": "user", "content": "follow-up"},
            ],
        )

    async def test_history_messages_with_images_keeps_current_message_multimodal(self):
        import json as json_module

        seen_bodies = []

        async def handler(request):
            seen_bodies.append(request.content)
            return httpx.Response(200, content=_sse_body("[DONE]"))

        client = _mock_client(handler)
        history = [{"role": "user", "content": "earlier"}, {"role": "assistant", "content": "reply"}]
        data_url = "data:image/png;base64,iVBORw0KGgo="
        async for _ in stream_order(
            "vendor/vision-model:free",
            "what is this",
            api_key="k",
            http_client=client,
            image_data_urls=[data_url],
            history_messages=history,
        ):
            pass
        await client.aclose()

        payload = json_module.loads(seen_bodies[0])
        self.assertEqual(len(payload["messages"]), 3)
        self.assertEqual(payload["messages"][0], {"role": "user", "content": "earlier"})
        self.assertIsInstance(payload["messages"][2]["content"], list)


if __name__ == "__main__":
    unittest.main()
