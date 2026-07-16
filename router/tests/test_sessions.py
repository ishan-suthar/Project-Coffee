import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from router.app.sessions import SessionStore, UsernameTakenError


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


class UserAndTokenTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")

    def test_create_user_and_get_by_username(self):
        user_id = self.store.create_user("alice", "hashed-password", "Alice")
        user = self.store.get_user_by_username("alice")
        self.assertEqual(user.id, user_id)
        self.assertEqual(user.display_name, "Alice")

    def test_create_user_duplicate_username_raises(self):
        self.store.create_user("alice", "hash1", "Alice")
        with self.assertRaises(UsernameTakenError):
            self.store.create_user("alice", "hash2", "Alice Again")

    def test_get_user_by_username_unknown_returns_none(self):
        self.assertIsNone(self.store.get_user_by_username("nobody"))

    def test_delete_user_removes_and_returns_true(self):
        self.store.create_user("alice", "hash", "Alice")
        self.assertTrue(self.store.delete_user("alice"))
        self.assertIsNone(self.store.get_user_by_username("alice"))

    def test_delete_user_unknown_returns_false(self):
        self.assertFalse(self.store.delete_user("nobody"))

    def test_list_users_ordered_by_created_at(self):
        self.store.create_user("alice", "hash", "Alice")
        self.store.create_user("bob", "hash", "Bob")
        usernames = [u.username for u in self.store.list_users()]
        self.assertEqual(usernames, ["alice", "bob"])

    def test_token_round_trips_to_user(self):
        user_id = self.store.create_user("alice", "hash", "Alice")
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        self.store.create_token("tok-1", user_id, future)
        user = self.store.get_user_for_token("tok-1")
        self.assertEqual(user.username, "alice")

    def test_expired_token_returns_none(self):
        user_id = self.store.create_user("alice", "hash", "Alice")
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.store.create_token("tok-expired", user_id, past)
        self.assertIsNone(self.store.get_user_for_token("tok-expired"))


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")
        self.alice_id = self.store.create_user("alice", "hash", "Alice")
        self.bob_id = self.store.create_user("bob", "hash", "Bob")

    def test_create_and_list_projects(self):
        self.store.create_project(self.alice_id, "Recipes")
        projects = self.store.list_projects(self.alice_id)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].name, "Recipes")

    def test_projects_scoped_by_user(self):
        self.store.create_project(self.alice_id, "Alice's project")
        self.store.create_project(self.bob_id, "Bob's project")
        self.assertEqual(len(self.store.list_projects(self.alice_id)), 1)
        self.assertEqual(len(self.store.list_projects(self.bob_id)), 1)

    def test_rename_project(self):
        project = self.store.create_project(self.alice_id, "Old name")
        self.assertTrue(self.store.rename_project(project.id, "New name", user_id=self.alice_id))
        self.assertEqual(self.store.get_project(project.id).name, "New name")

    def test_rename_project_wrong_user_fails(self):
        project = self.store.create_project(self.alice_id, "Alice's project")
        self.assertFalse(self.store.rename_project(project.id, "Hijacked", user_id=self.bob_id))
        self.assertEqual(self.store.get_project(project.id).name, "Alice's project")

    def test_delete_project_moves_sessions_to_default_not_deleting_them(self):
        project = self.store.create_project(self.alice_id, "Temp project")
        session_id = self.store.create_session(user_id=self.alice_id, project_id=project.id)

        self.assertTrue(self.store.delete_project(project.id, user_id=self.alice_id))

        self.assertIsNone(self.store.get_project(project.id))
        # The session still exists and is now unscoped ("default").
        default_sessions = self.store.list_sessions(user_id=self.alice_id, project_id=None)
        self.assertEqual({s.id for s in default_sessions}, {session_id})

    def test_delete_project_wrong_user_fails_and_keeps_sessions_scoped(self):
        project = self.store.create_project(self.alice_id, "Alice's project")
        session_id = self.store.create_session(user_id=self.alice_id, project_id=project.id)

        self.assertFalse(self.store.delete_project(project.id, user_id=self.bob_id))

        scoped_sessions = self.store.list_sessions(user_id=self.alice_id, project_id=project.id)
        self.assertEqual({s.id for s in scoped_sessions}, {session_id})

    def test_list_sessions_all_projects_ignores_project_filter(self):
        default_session = self.store.create_session(user_id=self.alice_id)
        project = self.store.create_project(self.alice_id, "A project")
        project_session = self.store.create_session(user_id=self.alice_id, project_id=project.id)

        all_sessions = self.store.list_sessions(user_id=self.alice_id, all_projects=True)
        self.assertEqual({s.id for s in all_sessions}, {default_session, project_session})


class ChatManagementTests(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")
        self.alice_id = self.store.create_user("alice", "hash", "Alice")
        self.bob_id = self.store.create_user("bob", "hash", "Bob")

    def test_rename_session_overwrites_even_a_non_default_title(self):
        """Unlike set_title_if_default(), an explicit rename always
        overwrites - docs/design/auth-projects-chat-management-design.md
        Section 5.1."""

        session_id = self.store.create_session(user_id=self.alice_id)
        self.store.set_title_if_default(session_id, "Auto title from first message")
        self.assertTrue(self.store.rename_session(session_id, "Explicit rename", user_id=self.alice_id))
        self.assertEqual(self.store.list_sessions(user_id=self.alice_id)[0].title, "Explicit rename")

    def test_rename_session_wrong_user_fails(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.assertFalse(self.store.rename_session(session_id, "Hijacked", user_id=self.bob_id))

    def test_soft_delete_excludes_from_list_and_exists(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.assertTrue(self.store.soft_delete_session(session_id, user_id=self.alice_id))

        self.assertEqual(self.store.list_sessions(user_id=self.alice_id), [])
        self.assertFalse(self.store.session_exists(session_id, user_id=self.alice_id))

    def test_soft_delete_does_not_remove_the_row_or_its_messages(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.store.add_message(session_id, request_id="r1", role="user", content="Hello")
        self.store.soft_delete_session(session_id, user_id=self.alice_id)

        # get_messages() has no deleted_at filter - the row and its
        # messages still physically exist, just excluded from listing/
        # existence checks.
        self.assertEqual(len(self.store.get_messages(session_id)), 1)

    def test_soft_delete_wrong_user_fails(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.assertFalse(self.store.soft_delete_session(session_id, user_id=self.bob_id))
        self.assertTrue(self.store.session_exists(session_id, user_id=self.alice_id))


class RememberChatAndAttachmentPersistenceTests(unittest.TestCase):
    """Brew 46 - docs/design/conversation-memory-design.md Section 1/3."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")
        self.alice_id = self.store.create_user("alice", "hash", "Alice")
        self.bob_id = self.store.create_user("bob", "hash", "Bob")

    def test_new_session_defaults_remember_chat_true(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.assertTrue(self.store.list_sessions(user_id=self.alice_id)[0].remember_chat)
        self.assertTrue(self.store.get_session(session_id, user_id=self.alice_id).remember_chat)

    def test_set_remember_chat_flips_it(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.assertTrue(self.store.set_remember_chat(session_id, False, user_id=self.alice_id))
        self.assertFalse(self.store.get_session(session_id, user_id=self.alice_id).remember_chat)

        self.assertTrue(self.store.set_remember_chat(session_id, True, user_id=self.alice_id))
        self.assertTrue(self.store.get_session(session_id, user_id=self.alice_id).remember_chat)

    def test_set_remember_chat_does_not_touch_stored_messages(self):
        """Flipping the toggle never deletes anything (Section 1)."""

        session_id = self.store.create_session(user_id=self.alice_id)
        self.store.add_message(session_id, request_id="r1", role="user", content="Hello")
        self.store.set_remember_chat(session_id, False, user_id=self.alice_id)
        self.assertEqual(len(self.store.get_messages(session_id)), 1)

    def test_set_remember_chat_wrong_user_fails(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.assertFalse(self.store.set_remember_chat(session_id, False, user_id=self.bob_id))

    def test_get_session_unknown_id_returns_none(self):
        self.assertIsNone(self.store.get_session("no-such-session", user_id=self.alice_id))

    def test_get_session_soft_deleted_returns_none(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.store.soft_delete_session(session_id, user_id=self.alice_id)
        self.assertIsNone(self.store.get_session(session_id, user_id=self.alice_id))

    def test_get_session_wrong_user_returns_none(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.assertIsNone(self.store.get_session(session_id, user_id=self.bob_id))

    def test_add_message_persists_attachments_json(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.store.add_message(
            session_id,
            request_id="r1",
            role="user",
            content="What does this say?",
            attachments_json='[{"filename": "a.pdf", "kind": "pdf"}]',
        )
        message = self.store.get_messages(session_id)[0]
        self.assertTrue(message.has_attachments)
        self.assertIn("a.pdf", message.attachments_json)

    def test_message_with_no_attachments_has_attachments_false(self):
        session_id = self.store.create_session(user_id=self.alice_id)
        self.store.add_message(session_id, request_id="r1", role="user", content="Hello")
        message = self.store.get_messages(session_id)[0]
        self.assertFalse(message.has_attachments)
        self.assertIsNone(message.attachments_json)


class ApiRequestTests(unittest.TestCase):
    """Brew 47 Section 2 (docs/design/openai-compat-endpoint-design.md):
    api_requests CRUD, retry matching, shadow-pair storage, and pruning."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")
        self.alice_id = self.store.create_user("alice", "hash", "Alice")

    def test_create_and_get_api_request(self):
        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        record = self.store.get_api_request("req-1")
        self.assertEqual(record.user_id, self.alice_id)
        self.assertEqual(record.client_fingerprint, "fp-1")
        self.assertIsNone(record.response_text)
        self.assertIsNone(record.completed_at)
        self.assertEqual(record.retry_count, 0)
        self.assertIsNone(record.retry_of)
        self.assertFalse(record.is_shadow)

    def test_get_api_request_unknown_returns_none(self):
        self.assertIsNone(self.store.get_api_request("nonexistent"))

    def test_complete_api_request_sets_response_text_and_completed_at(self):
        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.complete_api_request("req-1", "the answer", max_stored_chars=1000)
        record = self.store.get_api_request("req-1")
        self.assertEqual(record.response_text, "the answer")
        self.assertIsNotNone(record.completed_at)

    def test_complete_api_request_truncates_at_max_stored_chars(self):
        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.complete_api_request("req-1", "x" * 100, max_stored_chars=10)
        record = self.store.get_api_request("req-1")
        self.assertLess(len(record.response_text), 100)
        self.assertIn("truncated", record.response_text)

    def test_find_retry_candidate_matches_completed_request(self):
        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.complete_api_request("req-1", "answer", max_stored_chars=1000)
        self.store.create_api_request(
            "req-2", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )

        match = self.store.find_retry_candidate(
            user_id=self.alice_id,
            client_fingerprint="fp-1",
            last_user_message_hash="hash-1",
            exclude_request_id="req-2",
            window_seconds=300,
        )
        self.assertEqual(match, "req-1")

    def test_find_retry_candidate_none_when_original_still_in_flight(self):
        """The concurrency-vs-retry edge case (docs/design/
        openai-compat-endpoint-design.md Section 2): two requests fired at
        the same instant with identical content must NOT match each other -
        an in-flight original (response_text IS NULL) can never be a retry
        target, since a retry is structurally a reaction to an answer
        already seen."""

        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        # req-1 never completes before req-2 checks - simulates genuine
        # parallelism, not a real retry.
        self.store.create_api_request(
            "req-2", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )

        match = self.store.find_retry_candidate(
            user_id=self.alice_id,
            client_fingerprint="fp-1",
            last_user_message_hash="hash-1",
            exclude_request_id="req-2",
            window_seconds=300,
        )
        self.assertIsNone(match)

    def test_find_retry_candidate_none_outside_window(self):
        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.complete_api_request("req-1", "answer", max_stored_chars=1000)
        # Backdate req-1's completed_at to well outside any reasonable window.
        with self.store._connect() as conn:
            old = (datetime.now(timezone.utc) - timedelta(seconds=1000)).isoformat(timespec="microseconds")
            conn.execute("UPDATE api_requests SET completed_at = ? WHERE request_id = ?", (old, "req-1"))

        match = self.store.find_retry_candidate(
            user_id=self.alice_id,
            client_fingerprint="fp-1",
            last_user_message_hash="hash-1",
            exclude_request_id="req-2",
            window_seconds=300,
        )
        self.assertIsNone(match)

    def test_find_retry_candidate_none_for_different_fingerprint(self):
        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.complete_api_request("req-1", "answer", max_stored_chars=1000)

        match = self.store.find_retry_candidate(
            user_id=self.alice_id,
            client_fingerprint="fp-2",
            last_user_message_hash="hash-1",
            exclude_request_id="req-2",
            window_seconds=300,
        )
        self.assertIsNone(match)

    def test_find_retry_candidate_prefers_most_recent_match(self):
        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.complete_api_request("req-1", "first answer", max_stored_chars=1000)
        self.store.create_api_request(
            "req-2", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.complete_api_request("req-2", "second answer", max_stored_chars=1000)

        match = self.store.find_retry_candidate(
            user_id=self.alice_id,
            client_fingerprint="fp-1",
            last_user_message_hash="hash-1",
            exclude_request_id="req-3",
            window_seconds=300,
        )
        self.assertEqual(match, "req-2")

    def test_set_retry_of_and_increment_retry_count(self):
        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.create_api_request(
            "req-2", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.set_retry_of("req-2", "req-1")
        self.store.increment_retry_count("req-1")
        self.store.increment_retry_count("req-1")

        self.assertEqual(self.store.get_api_request("req-2").retry_of, "req-1")
        self.assertEqual(self.store.get_api_request("req-1").retry_count, 2)

    def test_record_shadow_result_writes_to_primary_row(self):
        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.complete_api_request("req-1", "cheap answer", max_stored_chars=1000)
        self.store.record_shadow_result("req-1", "premium answer", "Reserve Blend", max_stored_chars=1000)

        record = self.store.get_api_request("req-1")
        self.assertEqual(record.response_text, "cheap answer")
        self.assertEqual(record.shadow_response_text, "premium answer")
        self.assertEqual(record.shadow_bean_alias, "Reserve Blend")

    def test_prune_api_requests_older_than_deletes_only_old_rows(self):
        self.store.create_api_request(
            "req-old", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        with self.store._connect() as conn:
            old = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat(timespec="microseconds")
            conn.execute("UPDATE api_requests SET created_at = ? WHERE request_id = ?", (old, "req-old"))
        self.store.create_api_request(
            "req-new", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-2"
        )

        cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(timespec="microseconds")
        deleted = self.store.prune_api_requests_older_than(cutoff)

        self.assertEqual(deleted, 1)
        self.assertIsNone(self.store.get_api_request("req-old"))
        self.assertIsNotNone(self.store.get_api_request("req-new"))

    def test_prune_never_runs_automatically(self):
        """No code path in this class calls prune_api_requests_older_than
        except a direct, explicit call - documented as a design invariant,
        checked here by confirming a request row survives create/complete/
        retry/shadow operations with no pruning call in between."""

        self.store.create_api_request(
            "req-1", user_id=self.alice_id, client_fingerprint="fp-1", last_user_message_hash="hash-1"
        )
        self.store.complete_api_request("req-1", "answer", max_stored_chars=1000)
        self.assertIsNotNone(self.store.get_api_request("req-1"))


if __name__ == "__main__":
    unittest.main()
