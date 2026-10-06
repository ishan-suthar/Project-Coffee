import json
import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from router.app.aliases import BeanRegistry
from router.app.events import (
    CancelledEvent,
    ClassifyingEvent,
    CompleteEvent,
    EscalatingEvent,
    EscalationPendingEvent,
    ErrorEvent,
    GeneratingEvent,
    HeartbeatEvent,
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

    def test_escalation_pending_decision_deadline_defaults_to_none(self):
        """v1.3: decision_deadline is additive and optional - old-style
        EscalationPendingEvent construction (no decision_deadline) must
        still work."""

        event = EscalationPendingEvent(
            request_id=REQUEST_ID,
            reason="truncated",
            est_cost_usd=0.42,
            premium_bean_alias="Reserve Blend",
        )
        self.assertIsNone(event.decision_deadline)

    def test_escalation_pending_decision_deadline_round_trips(self):
        deadline = datetime(2026, 7, 12, 20, 30, 0, tzinfo=timezone.utc)
        event = EscalationPendingEvent(
            request_id=REQUEST_ID,
            reason="truncated",
            est_cost_usd=0.42,
            premium_bean_alias="Reserve Blend",
            decision_deadline=deadline,
        )
        frame = event.to_sse()
        payload = json.loads(frame[len("data: "):].strip())
        self.assertIn("2026-07-12T20:30:00", payload["decision_deadline"])

    def test_heartbeat_event_shape(self):
        event = HeartbeatEvent(request_id=REQUEST_ID)
        self.assertEqual(event.event, "heartbeat")
        frame = event.to_sse()
        payload = json.loads(frame[len("data: "):].strip())
        self.assertEqual(payload["event"], "heartbeat")
        self.assertEqual(payload["request_id"], REQUEST_ID)

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

    def test_complete_event_pantry_sources_defaults_to_none(self):
        """v1.4: pantry_sources is additive and optional - old-style
        CompleteEvent construction (no pantry_sources) must still work."""

        event = CompleteEvent(
            request_id=REQUEST_ID,
            bean_alias="House Blend",
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.0,
            latency_ms=100,
            escalated=False,
            draft_quality=False,
        )
        self.assertIsNone(event.pantry_sources)

    def test_complete_event_pantry_sources_round_trips(self):
        event = CompleteEvent(
            request_id=REQUEST_ID,
            bean_alias="House Blend",
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.0,
            latency_ms=100,
            escalated=False,
            draft_quality=False,
            pantry_sources=["knowledge/00_index.md", "knowledge/README.md"],
        )
        frame = event.to_sse()
        payload = json.loads(frame[len("data: "):].strip())
        self.assertEqual(payload["pantry_sources"], ["knowledge/00_index.md", "knowledge/README.md"])

    def test_complete_event_v17_trim_fields_default_to_none(self):
        """v1.7: additive and optional - old-style CompleteEvent
        construction with no trim fields must still work."""

        event = CompleteEvent(
            request_id=REQUEST_ID,
            bean_alias="House Blend",
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.0,
            latency_ms=100,
            escalated=False,
            draft_quality=False,
        )
        self.assertIsNone(event.history_turns_dropped)
        self.assertIsNone(event.history_chars_dropped)
        self.assertIsNone(event.history_drop_reason)

    def test_complete_event_v17_trim_fields_round_trip(self):
        event = CompleteEvent(
            request_id=REQUEST_ID,
            bean_alias="House Blend",
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.0,
            latency_ms=100,
            escalated=False,
            draft_quality=False,
            history_turns=2,
            history_tokens_est=400,
            history_turns_dropped=3,
            history_chars_dropped=31804,
            history_drop_reason="single_turn_too_large",
        )
        frame = event.to_sse()
        payload = json.loads(frame[len("data: "):].strip())

        self.assertEqual(payload["history_turns_dropped"], 3)
        self.assertEqual(payload["history_chars_dropped"], 31804)
        self.assertEqual(payload["history_drop_reason"], "single_turn_too_large")

    def test_complete_event_rejects_an_unknown_drop_reason(self):
        """The reason is a closed set - a typo must fail loudly here
        rather than reaching a UI that has no copy for it."""

        with self.assertRaises(ValidationError):
            CompleteEvent(
                request_id=REQUEST_ID,
                bean_alias="House Blend",
                tokens_in=10,
                tokens_out=20,
                cost_usd=0.0,
                latency_ms=100,
                escalated=False,
                draft_quality=False,
                history_drop_reason="somebody_made_this_up",
            )

    def test_generating_event_has_no_history_trim_fields(self):
        """v1.7 fields live on `complete` only - a consumer must never be
        able to read half a trim picture off a mid-stream tick."""

        for field in (
            "history_turns_dropped",
            "history_chars_dropped",
            "history_drop_reason",
        ):
            self.assertNotIn(field, GeneratingEvent.model_fields)

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
            HeartbeatEvent(request_id=REQUEST_ID),
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
