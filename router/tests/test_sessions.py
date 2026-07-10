import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from router.app.sessions import SessionStore


class SessionStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")

    def test_create_session_returns_id_and_is_listed(self):
        session_id = self.store.create_session("project-a")
        sessions = self.store.list_sessions("project-a")
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].id, session_id)
        self.assertEqual(sessions[0].title, "New session")
        self.assertEqual(sessions[0].cost_total_usd, 0.0)

    def test_sessions_scoped_by_project(self):
        self.store.create_session("project-a")
        self.store.create_session("project-b")
        self.assertEqual(len(self.store.list_sessions("project-a")), 1)
        self.assertEqual(len(self.store.list_sessions("project-b")), 1)
        self.assertEqual(len(self.store.list_sessions("project-c")), 0)

    def test_add_message_updates_session_updated_at_and_cost_total(self):
        session_id = self.store.create_session("project-a")
        before = self.store.list_sessions("project-a")[0].updated_at

        self.store.add_message(
            session_id,
            request_id="req-1",
            role="user",
            content="Hello",
        )
        self.store.add_message(
            session_id,
            request_id="req-1",
            role="assistant",
            content="Hi there",
            bean_alias="House Blend",
            task_type="explain",
            complexity="espresso_shot",
            cost_usd=0.02,
            latency_ms=1200,
            escalated=False,
            draft_quality=False,
        )

        sessions = self.store.list_sessions("project-a")
        self.assertEqual(sessions[0].cost_total_usd, 0.02)
        self.assertGreaterEqual(sessions[0].updated_at, before)

    def test_get_messages_returns_in_order(self):
        session_id = self.store.create_session("project-a")
        self.store.add_message(session_id, request_id="req-1", role="user", content="First")
        self.store.add_message(session_id, request_id="req-1", role="assistant", content="Second")

        messages = self.store.get_messages(session_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].content, "First")
        self.assertEqual(messages[1].content, "Second")

    def test_assistant_message_stores_all_metadata(self):
        session_id = self.store.create_session("project-a")
        self.store.add_message(
            session_id,
            request_id="req-1",
            role="assistant",
            content="Answer",
            bean_alias="House Blend",
            task_type="code",
            complexity="cold_brew",
            cost_usd=0.05,
            latency_ms=3000,
            escalated=True,
            draft_quality=False,
        )
        message = self.store.get_messages(session_id)[0]
        self.assertEqual(message.bean_alias, "House Blend")
        self.assertEqual(message.task_type, "code")
        self.assertEqual(message.complexity, "cold_brew")
        self.assertEqual(message.cost_usd, 0.05)
        self.assertEqual(message.latency_ms, 3000)
        self.assertTrue(message.escalated)
        self.assertFalse(message.draft_quality)
        self.assertIsNone(message.rating)

    def test_user_message_has_null_assistant_fields(self):
        session_id = self.store.create_session("project-a")
        self.store.add_message(session_id, request_id="req-1", role="user", content="Hi")
        message = self.store.get_messages(session_id)[0]
        self.assertIsNone(message.bean_alias)
        self.assertIsNone(message.escalated)
        self.assertIsNone(message.draft_quality)

    def test_set_title_if_default_sets_title(self):
        session_id = self.store.create_session("project-a")
        self.store.set_title_if_default(session_id, "Explain decorators please and also more")
        sessions = self.store.list_sessions("project-a")
        self.assertEqual(sessions[0].title, "Explain decorators please and also more")

    def test_set_title_if_default_does_not_overwrite_existing_title(self):
        session_id = self.store.create_session("project-a")
        self.store.set_title_if_default(session_id, "First title")
        self.store.set_title_if_default(session_id, "Second title")
        sessions = self.store.list_sessions("project-a")
        self.assertEqual(sessions[0].title, "First title")

    def test_title_truncated_to_max_chars(self):
        session_id = self.store.create_session("project-a")
        long_title = "x" * 200
        self.store.set_title_if_default(session_id, long_title)
        sessions = self.store.list_sessions("project-a")
        self.assertEqual(len(sessions[0].title), 80)

    def test_update_message_rating_returns_true_when_found(self):
        session_id = self.store.create_session("project-a")
        self.store.add_message(session_id, request_id="req-1", role="assistant", content="Answer")
        updated = self.store.update_message_rating("req-1", "good")
        self.assertTrue(updated)
        message = self.store.get_messages(session_id)[0]
        self.assertEqual(message.rating, "good")

    def test_update_message_rating_returns_false_when_not_found(self):
        updated = self.store.update_message_rating("nonexistent-request-id", "good")
        self.assertFalse(updated)

    def test_session_exists(self):
        session_id = self.store.create_session("project-a")
        self.assertTrue(self.store.session_exists(session_id))
        self.assertFalse(self.store.session_exists("nonexistent-id"))

    def test_list_sessions_ordered_newest_updated_first(self):
        first = self.store.create_session("project-a")
        second = self.store.create_session("project-a")
        # Touch `first` again so it becomes the most recently updated.
        self.store.add_message(first, request_id="req-1", role="user", content="Hi")

        sessions = self.store.list_sessions("project-a")
        self.assertEqual(sessions[0].id, first)
        self.assertEqual(sessions[1].id, second)


if __name__ == "__main__":
    unittest.main()
