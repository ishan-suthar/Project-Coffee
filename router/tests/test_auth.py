import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import yaml

from router.app.aliases import Bean, BeanRegistry
from router.app.auth import InvalidCredentialsError, hash_password, login
from router.app.config import Settings
from router.app.ledger import RouterLedger
from router.app.main import RouterState, create_app
from router.app.routing import RoutingPolicy
from router.app.sessions import SessionStore

FIXTURE_POLICY = {"task_types": {}}


def _make_bean_registry() -> BeanRegistry:
    return BeanRegistry(
        [
            Bean(
                alias="House Blend",
                role="default",
                model_id="vendor/default:free",
                vision=False,
                code=True,
                price_per_1k_input_usd=0.0,
                price_per_1k_output_usd=0.0,
                status="active",
            )
        ]
    )


class AuthHelperTests(unittest.TestCase):
    """router/app/auth.py's pure functions, no HTTP involved."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")

    def test_login_success_returns_token_and_user(self):
        self.store.create_user("alice", hash_password("hunter2"), "Alice")
        token, user = login(self.store, "alice", "hunter2")
        self.assertEqual(len(token), 64)
        self.assertEqual(user.username, "alice")
        self.assertEqual(user.display_name, "Alice")

    def test_login_wrong_password_raises(self):
        self.store.create_user("alice", hash_password("hunter2"), "Alice")
        with self.assertRaises(InvalidCredentialsError):
            login(self.store, "alice", "wrong-password")

    def test_login_unknown_username_raises(self):
        with self.assertRaises(InvalidCredentialsError):
            login(self.store, "nobody", "whatever")

    def test_wrong_password_and_unknown_username_give_identical_message(self):
        self.store.create_user("alice", hash_password("hunter2"), "Alice")
        try:
            login(self.store, "alice", "wrong-password")
            self.fail("expected InvalidCredentialsError")
        except InvalidCredentialsError as exc:
            wrong_password_message = str(exc)
        try:
            login(self.store, "nobody", "whatever")
            self.fail("expected InvalidCredentialsError")
        except InvalidCredentialsError as exc:
            unknown_user_message = str(exc)
        self.assertEqual(wrong_password_message, unknown_user_message)

    def test_get_user_for_token_returns_none_for_expired_token(self):
        user_id = self.store.create_user("alice", hash_password("hunter2"), "Alice")
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.store.create_token("expired-token", user_id, past)
        self.assertIsNone(self.store.get_user_for_token("expired-token"))

    def test_get_user_for_token_returns_user_for_live_token(self):
        user_id = self.store.create_user("alice", hash_password("hunter2"), "Alice")
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        self.store.create_token("live-token", user_id, future)
        user = self.store.get_user_for_token("live-token")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "alice")

    def test_delete_token_invalidates_it(self):
        user_id = self.store.create_user("alice", hash_password("hunter2"), "Alice")
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        self.store.create_token("live-token", user_id, future)
        self.assertTrue(self.store.delete_token("live-token"))
        self.assertIsNone(self.store.get_user_for_token("live-token"))


class AuthEndpointTests(unittest.IsolatedAsyncioTestCase):
    """POST /v1/login, POST /v1/logout, and the get_current_user
    dependency exercised through the real HTTP surface - the only place
    in the whole test suite that sends a real Authorization header
    rather than using app.dependency_overrides (docs/design/
    auth-projects-chat-management-design.md Section 3.1, Gap 3)."""

    def setUp(self):
        self._tmp_dir = TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        policy_path = Path(self._tmp_dir.name) / "routing_policy.yaml"
        with open(policy_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(FIXTURE_POLICY, handle)

        registry = _make_bean_registry()
        policy = RoutingPolicy.from_yaml(policy_path, bean_registry=registry)
        settings = Settings()
        ledger = RouterLedger(Path(self._tmp_dir.name) / "router_requests.csv")
        self.session_store = SessionStore(Path(self._tmp_dir.name) / "sessions.db")
        self.state = RouterState(
            bean_registry=registry,
            routing_policy=policy,
            settings=settings,
            ledger=ledger,
            session_store=self.session_store,
            uploads_root=Path(self._tmp_dir.name) / "uploads",
        )
        self.app = create_app(state=self.state)
        self.session_store.create_user("alice", hash_password("hunter2"), "Alice")
        self.session_store.create_user("bob", hash_password("swordfish"), "Bob")

    async def _login(self, client, username, password):
        response = await client.post("/v1/login", json={"username": username, "password": password})
        return response

    async def test_login_success(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await self._login(client, "alice", "hunter2")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["token"]), 64)
        self.assertEqual(body["user"]["username"], "alice")
        self.assertEqual(body["user"]["display_name"], "Alice")

    async def test_login_failure_wrong_password(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await self._login(client, "alice", "wrong-password")
        self.assertEqual(response.status_code, 401)

    async def test_login_failure_unknown_username(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await self._login(client, "nobody", "whatever")
        self.assertEqual(response.status_code, 401)

    async def test_missing_authorization_header_returns_401(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/beans")
        self.assertEqual(response.status_code, 401)

    async def test_malformed_authorization_header_returns_401(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/beans", headers={"Authorization": "not-a-bearer-token"})
        self.assertEqual(response.status_code, 401)

    async def test_unknown_token_returns_401(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/beans", headers={"Authorization": "Bearer nonexistent-token"})
        self.assertEqual(response.status_code, 401)

    async def test_expired_token_returns_401(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        user = self.session_store.get_user_by_username("alice")
        self.session_store.create_token("expired-token", user.id, past)

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/beans", headers={"Authorization": "Bearer expired-token"})
        self.assertEqual(response.status_code, 401)

    async def test_valid_token_grants_access(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            login_response = await self._login(client, "alice", "hunter2")
            token = login_response.json()["token"]
            response = await client.get("/v1/beans", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)

    async def test_logout_invalidates_token(self):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            login_response = await self._login(client, "alice", "hunter2")
            token = login_response.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}

            logout_response = await client.post("/v1/logout", headers=headers)
            self.assertEqual(logout_response.status_code, 200)

            after_logout = await client.get("/v1/beans", headers=headers)
        self.assertEqual(after_logout.status_code, 401)

    async def test_user_isolation_sessions(self):
        """Two real users, each with a session created through the real
        HTTP surface - user A's token must never see user B's session,
        neither in the list nor when addressed directly by id."""

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            alice_token = (await self._login(client, "alice", "hunter2")).json()["token"]
            bob_token = (await self._login(client, "bob", "swordfish")).json()["token"]
            alice_headers = {"Authorization": f"Bearer {alice_token}"}
            bob_headers = {"Authorization": f"Bearer {bob_token}"}

            alice_session = (await client.post("/v1/sessions", json={}, headers=alice_headers)).json()
            bob_session = (await client.post("/v1/sessions", json={}, headers=bob_headers)).json()

            alice_list = (await client.get("/v1/sessions", headers=alice_headers)).json()
            bob_list = (await client.get("/v1/sessions", headers=bob_headers)).json()

        self.assertEqual({s["id"] for s in alice_list}, {alice_session["id"]})
        self.assertEqual({s["id"] for s in bob_list}, {bob_session["id"]})

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            cross_access = await client.get(
                f"/v1/sessions/{bob_session['id']}/messages", headers=alice_headers
            )
        self.assertEqual(cross_access.status_code, 404)

    async def test_user_isolation_projects(self):
        """Two real users, each with a real project - user A must never
        see, rename, or delete user B's project."""

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            alice_token = (await self._login(client, "alice", "hunter2")).json()["token"]
            bob_token = (await self._login(client, "bob", "swordfish")).json()["token"]
            alice_headers = {"Authorization": f"Bearer {alice_token}"}
            bob_headers = {"Authorization": f"Bearer {bob_token}"}

            alice_project = (
                await client.post("/v1/projects", json={"name": "Alice's project"}, headers=alice_headers)
            ).json()
            bob_project = (
                await client.post("/v1/projects", json={"name": "Bob's project"}, headers=bob_headers)
            ).json()

            alice_list = (await client.get("/v1/projects", headers=alice_headers)).json()
            bob_list = (await client.get("/v1/projects", headers=bob_headers)).json()

        self.assertEqual({p["id"] for p in alice_list}, {alice_project["id"]})
        self.assertEqual({p["id"] for p in bob_list}, {bob_project["id"]})

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            rename_attempt = await client.patch(
                f"/v1/projects/{bob_project['id']}", json={"name": "Hijacked"}, headers=alice_headers
            )
            delete_attempt = await client.delete(
                f"/v1/projects/{bob_project['id']}", headers=alice_headers
            )
        self.assertEqual(rename_attempt.status_code, 404)
        self.assertEqual(delete_attempt.status_code, 404)


if __name__ == "__main__":
    unittest.main()
