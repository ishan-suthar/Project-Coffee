import json
import unittest

from router.app.aliases import BeanRegistry
from router.app.events import (
    CancelledEvent,
    ClassifyingEvent,
    CompleteEvent,
    EscalatingEvent,
    EscalationPendingEvent,
    ErrorEvent,
    GeneratingEvent,
    OrderReceivedEvent,
    RouteSelectedEvent,
)

REQUEST_ID = "test-request-id"


class EventContractTests(unittest.TestCase):
    def test_order_received_event_shape(self):
        event = OrderReceivedEvent(request_id=REQUEST_ID, prompt_chars=812)
        self.assertEqual(event.event, "order_received")
        self.assertEqual(event.prompt_chars, 812)

    def test_route_selected_event_shape(self):
        event = RouteSelectedEvent(
            request_id=REQUEST_ID,
            bean_alias="House Blend",
            task_type="code",
            complexity="espresso_shot",
            est_cost_usd=0.0,
            policy_entry="code/nvidia-nemotron-3-ultra",
        )
        self.assertEqual(event.complexity, "espresso_shot")

    def test_route_selected_constraint_reason_defaults_to_none(self):
        """v1.2: constraint_reason is additive and optional - old-style
        RouteSelectedEvent construction (no constraint_reason) must still
        work."""

        event = RouteSelectedEvent(
            request_id=REQUEST_ID,
            bean_alias="House Blend",
            task_type="code",
            complexity="espresso_shot",
            est_cost_usd=0.0,
            policy_entry="code/house-blend",
        )
        self.assertIsNone(event.constraint_reason)

    def test_route_selected_constraint_reason_round_trips(self):
        event = RouteSelectedEvent(
            request_id=REQUEST_ID,
            bean_alias="Vision Blend",
            task_type="explain",
            complexity="espresso_shot",
            est_cost_usd=0.0,
            policy_entry="explain/house-blend",
            constraint_reason="needs_vision: escalated from House Blend to Vision Blend",
        )
        frame = event.to_sse()
        payload = json.loads(frame[len("data: "):].strip())
        self.assertEqual(
            payload["constraint_reason"], "needs_vision: escalated from House Blend to Vision Blend"
        )

    def test_complexity_only_accepts_barista_charter_values(self):
        with self.assertRaises(ValueError):
            RouteSelectedEvent(
                request_id=REQUEST_ID,
                bean_alias="House Blend",
                task_type="code",
                complexity="medium",  # not a real Barista Charter work mode
                policy_entry="code/default",
            )

    def test_generating_event_text_delta_defaults_to_none(self):
        """v1.1: text_delta is additive and optional - old-style
        GeneratingEvent construction (no text_delta) must still work."""

        event = GeneratingEvent(request_id=REQUEST_ID, tokens_out=10, est_cost_usd=0.0)
        self.assertIsNone(event.text_delta)

    def test_generating_event_text_delta_round_trips(self):
        event = GeneratingEvent(
            request_id=REQUEST_ID, tokens_out=10, est_cost_usd=0.0, text_delta="Hello "
        )
        frame = event.to_sse()
        payload = json.loads(frame[len("data: "):].strip())
        self.assertEqual(payload["text_delta"], "Hello ")

    def test_to_sse_produces_data_frame(self):
        event = ClassifyingEvent(request_id=REQUEST_ID)
        frame = event.to_sse()
        self.assertTrue(frame.startswith("data: "))
        self.assertTrue(frame.endswith("\n\n"))
        payload = json.loads(frame[len("data: "):].strip())
        self.assertEqual(payload["event"], "classifying")
        self.assertEqual(payload["request_id"], REQUEST_ID)

    def test_escalation_pending_event_shape(self):
        event = EscalationPendingEvent(
            request_id=REQUEST_ID,
            reason="truncated",
            est_cost_usd=0.42,
            premium_bean_alias=None,
        )
        self.assertIsNone(event.premium_bean_alias)

    def test_complete_event_draft_quality_flag(self):
        event = CompleteEvent(
            request_id=REQUEST_ID,
            bean_alias="House Blend",
            tokens_in=210,
            tokens_out=640,
            cost_usd=0.0,
            latency_ms=2940,
            escalated=False,
            draft_quality=True,
        )
        self.assertTrue(event.draft_quality)

    def test_no_raw_model_id_ever_appears_in_any_event_payload(self):
        """Requirement 2: raw model IDs must never leak into event payloads."""

        registry = BeanRegistry.from_yaml()
        raw_ids = registry.known_model_ids()

        events = [
            OrderReceivedEvent(request_id=REQUEST_ID, prompt_chars=100),
            ClassifyingEvent(request_id=REQUEST_ID),
            RouteSelectedEvent(
                request_id=REQUEST_ID,
                bean_alias="House Blend",
                task_type="code",
                complexity="espresso_shot",
                est_cost_usd=0.0,
                policy_entry="code/default",
            ),
            GeneratingEvent(request_id=REQUEST_ID, tokens_out=10, est_cost_usd=0.0),
            EscalationPendingEvent(
                request_id=REQUEST_ID,
                reason="empty",
                est_cost_usd=0.1,
                premium_bean_alias="Reserve Blend",
            ),
            EscalatingEvent(request_id=REQUEST_ID, bean_alias="Reserve Blend"),
            CompleteEvent(
                request_id=REQUEST_ID,
                bean_alias="House Blend",
                tokens_in=10,
                tokens_out=20,
                cost_usd=0.0,
                latency_ms=100,
                escalated=False,
                draft_quality=False,
            ),
            ErrorEvent(
                request_id=REQUEST_ID,
                error_type="provider_timeout",
                message="OpenRouter did not respond within the configured timeout.",
                retryable=True,
            ),
            CancelledEvent(request_id=REQUEST_ID, reason="client_disconnect"),
        ]

        for event in events:
            frame = event.to_sse()
            for raw_id in raw_ids:
                self.assertNotIn(
                    raw_id,
                    frame,
                    msg=f"Raw model ID {raw_id!r} leaked into {event.event} event payload",
                )


if __name__ == "__main__":
    unittest.main()
