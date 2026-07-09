import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import yaml

from router.app.aliases import Bean, BeanRegistry
from router.app.config import Settings
from router.app.ledger import RouterLedger
from router.app.main import RouterState, create_app, run_order
from router.app.openrouter_client import StreamChunk
from router.app.routing import RoutingPolicy

FIXTURE_POLICY = {
    "task_types": {
        "code": {
            "status": "evidence_based",
            "primary_bean_alias": "House Blend",
            "fallback_bean_alias": "Second Pour",
            "premium_bean_alias": "Reserve Blend",
            "evidence": ["fixture"],
            "reason": "fixture",
        },
    }
}


def _make_bean_registry(with_premium: bool = True) -> BeanRegistry:
    beans = [
        Bean(
            alias="House Blend",
            role="default",
            model_id="vendor/default:free",
            vision=False,
            code=True,
            price_per_1k_input_usd=0.0,
            price_per_1k_output_usd=0.0,
            status="active",
        ),
        Bean(
            alias="Second Pour",
            role="fallback",
            model_id="vendor/fallback:free",
            vision=False,
            code=True,
            price_per_1k_input_usd=0.0,
            price_per_1k_output_usd=0.0,
            status="active",
        ),
    ]
    if with_premium:
        beans.append(
            Bean(
                alias="Reserve Blend",
                role="premium",
                model_id="vendor/premium",
                vision=False,
                code=True,
                price_per_1k_input_usd=1.0,
                price_per_1k_output_usd=2.0,
                status="active",
            )
        )
    else:
        beans.append(
            Bean(
                alias="Reserve Blend",
                role="premium",
                model_id=None,
                vision=False,
                code=True,
                price_per_1k_input_usd=None,
                price_per_1k_output_usd=None,
                status="not_yet_selected",
            )
        )
    return BeanRegistry(beans)


async def _fake_stream_healthy(model_id, prompt):
    for word in ["Hello ", "world " * 20]:
        yield StreamChunk(content_delta=word)
    yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 50})
    yield StreamChunk(is_final=True)


async def _fake_stream_empty(model_id, prompt):
    yield StreamChunk(finish_reason="stop", usage={"completion_tokens": 0})
    yield StreamChunk(is_final=True)


class RunOrderTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)
        self.policy_path = policy_path
        self.ledger_path = Path(self._tmp_dir.name) / "router_requests.csv"

    def _make_state(self, with_premium=True, escalation_cost_cap_usd=0.50):
        registry = _make_bean_registry(with_premium=with_premium)
        policy = RoutingPolicy.from_yaml(self.policy_path, bean_registry=registry)
        settings = Settings(
            escalation_cost_cap_usd=escalation_cost_cap_usd,
            generating_tick_tokens=5,
            generating_tick_seconds=999,
            truncation_min_expected_tokens=10,
            refusal_keywords=["i cannot help"],
        )
        ledger = RouterLedger(self.ledger_path)
        return RouterState(
            bean_registry=registry, routing_policy=policy, settings=settings, ledger=ledger
        )

    async def _collect(self, state, stream_fn, **kwargs):
        return [
            event
            async for event in run_order(state, prompt="Implement a function.", stream_order_fn=stream_fn, **kwargs)
        ]

    async def test_happy_path_event_order(self):
        state = self._make_state()
        events = await self._collect(state, _fake_stream_healthy)
        event_names = [e.event for e in events]
        self.assertEqual(
            event_names[:3], ["order_received", "classifying", "route_selected"]
        )
        self.assertIn("generating", event_names)
        self.assertEqual(event_names[-1], "complete")
        complete = events[-1]
        self.assertFalse(complete.escalated)
        self.assertFalse(complete.draft_quality)

    async def test_happy_path_writes_ledger_row(self):
        state = self._make_state()
        await self._collect(state, _fake_stream_healthy)
        rows = state.ledger.read_all_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bean_alias"], "House Blend")
        self.assertEqual(rows[0]["raw_model_id"], "vendor/default:free")
        self.assertEqual(rows[0]["escalation_approved"], "n/a")

    async def test_no_premium_available_produces_draft_quality(self):
        state = self._make_state(with_premium=False)
        events = await self._collect(state, _fake_stream_empty)
        event_names = [e.event for e in events]
        self.assertIn("escalation_pending", event_names)
        self.assertNotIn("escalating", event_names)
        complete = events[-1]
        self.assertTrue(complete.draft_quality)
        self.assertFalse(complete.escalated)
        pending_event = next(e for e in events if e.event == "escalation_pending")
        self.assertIsNone(pending_event.premium_bean_alias)

    async def test_auto_escalate_under_cap(self):
        # Reserve Blend cost: (tokens_in/1000 * 1.0) + (tokens_out/1000 * 2.0),
        # tiny prompt -> well under the 0.50 cap in this fixture's settings.
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.50)
        events = await self._collect(state, _fake_stream_empty)
        event_names = [e.event for e in events]
        self.assertIn("escalation_pending", event_names)
        self.assertIn("escalating", event_names)
        complete = events[-1]
        self.assertTrue(complete.escalated)
        self.assertEqual(complete.bean_alias, "Reserve Blend")

    async def test_escalation_pending_approved_escalates(self):
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)  # force pending, not auto

        async def approve(request_id):
            return "approved"

        events = await self._collect(state, _fake_stream_empty, wait_for_approval=approve)
        event_names = [e.event for e in events]
        self.assertIn("escalation_pending", event_names)
        self.assertIn("escalating", event_names)
        complete = events[-1]
        self.assertTrue(complete.escalated)
        self.assertFalse(complete.draft_quality)

    async def test_escalation_pending_declined_stays_draft(self):
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)

        async def decline(request_id):
            return "declined"

        events = await self._collect(state, _fake_stream_empty, wait_for_approval=decline)
        event_names = [e.event for e in events]
        self.assertIn("escalation_pending", event_names)
        self.assertNotIn("escalating", event_names)
        complete = events[-1]
        self.assertFalse(complete.escalated)
        self.assertTrue(complete.draft_quality)

    async def test_no_raw_model_id_in_any_yielded_event(self):
        state = self._make_state(with_premium=True, escalation_cost_cap_usd=0.0)

        async def approve(request_id):
            return "approved"

        events = await self._collect(state, _fake_stream_empty, wait_for_approval=approve)
        raw_ids = state.bean_registry.known_model_ids()
        for event in events:
            frame = event.to_sse()
            for raw_id in raw_ids:
                self.assertNotIn(raw_id, frame)


class FastApiSmokeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)

        registry = _make_bean_registry(with_premium=True)
        policy = RoutingPolicy.from_yaml(policy_path, bean_registry=registry)
        settings = Settings(generating_tick_tokens=5, generating_tick_seconds=999)
        ledger = RouterLedger(Path(self._tmp_dir.name) / "router_requests.csv")
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            stream_order_fn=_fake_stream_healthy,
        )
        self.app = create_app(state=self.state)

    async def test_order_endpoint_streams_sse_events(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream("POST", "/v1/order", json={"prompt": "Implement a function."}) as response:
                self.assertEqual(response.status_code, 200)
                body_lines = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        body_lines.append(json.loads(line[len("data: "):]))

        event_names = [item["event"] for item in body_lines]
        self.assertEqual(event_names[0], "order_received")
        self.assertEqual(event_names[-1], "complete")

    async def test_approve_escalation_resolves_pending_future(self):
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.state.pending_escalations["req-123"] = future

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/approve_escalation", json={"request_id": "req-123", "approve": True}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(await future, "approved")

    async def test_approve_escalation_unknown_request_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/approve_escalation", json={"request_id": "nonexistent", "approve": True}
            )
        self.assertEqual(response.status_code, 404)

    async def test_retry_unknown_request_id_404(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/retry", json={"request_id": "nonexistent"})
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
