import unittest

from tools import coffee_context_package


class ContextPackageTests(unittest.TestCase):
    def route(self) -> dict[str, object]:
        return {
            "request_class": "current_status",
            "selected_mode": "Local evidence only",
            "approval_required": False,
            "reason": "Use local Brew Log evidence.",
        }

    def evidence(self, path: str = "brew-log/progress.md", snippet: str = "Current status: Brew 34A") -> dict[str, object]:
        return {
            "source_path": path,
            "heading": "Current shot",
            "snippet": snippet,
            "score": 10,
            "reason_selected": "matched body",
            "freshness_signal": "current-status-file",
            "safety_classification": "local-project-note",
        }

    def test_builds_package_from_simple_request_and_evidence_item(self) -> None:
        package = coffee_context_package.build_context_package(
            request_text="What is the current Brew?",
            route_decision=self.route(),
            active_root="C:/Project_Coffee",
            evidence_items=[self.evidence()],
        )

        self.assertEqual(package["request_text"], "What is the current Brew?")
        self.assertEqual(package["route_decision"]["selected_mode"], "Local evidence only")
        self.assertEqual(package["active_root"], "C:/Project_Coffee")
        self.assertEqual(len(package["evidence_items"]), 1)
        self.assertEqual(package["package_status"], "preview_only")

    def test_defaults_user_approval_to_false(self) -> None:
        package = coffee_context_package.build_context_package(
            request_text="What is next?",
            route_decision=self.route(),
            active_root=".",
        )

        self.assertFalse(package["user_approval"]["approved"])
        self.assertIsNone(package["user_approval"]["approval_timestamp"])
        self.assertIsNone(package["user_approval"]["approved_context_hash"])

    def test_provider_model_is_not_selected(self) -> None:
        package = coffee_context_package.build_context_package(
            request_text="What is next?",
            route_decision=self.route(),
            active_root=".",
        )

        self.assertIsNone(package["provider_model"]["provider"])
        self.assertIsNone(package["provider_model"]["model"])
        self.assertEqual(package["provider_model"]["status"], "not_selected")

    def test_limits_evidence_items_by_max_context_items(self) -> None:
        package = coffee_context_package.build_context_package(
            request_text="Summarize status",
            route_decision=self.route(),
            active_root=".",
            evidence_items=[
                self.evidence(path="brew-log/progress.md"),
                self.evidence(path="brew-log/active_context.md"),
                self.evidence(path="ROADMAP.md"),
            ],
            max_context_items=2,
        )

        self.assertEqual(len(package["evidence_items"]), 2)

    def test_excludes_unsafe_env_paths(self) -> None:
        package = coffee_context_package.build_context_package(
            request_text="Include local config",
            route_decision=self.route(),
            active_root=".",
            evidence_items=[self.evidence(path=".env")],
        )

        self.assertFalse(package["evidence_items"][0]["included"])
        self.assertIn(".env", package["excluded_paths"][0]["path"])
        self.assertEqual(package["safety_checks"]["status"], "warning")

    def test_request_for_env_path_is_blocked_without_reading_file(self) -> None:
        package = coffee_context_package.build_context_package(
            request_text="Include my .env file in the context package.",
            route_decision=self.route(),
            active_root=".",
            evidence_items=[],
        )

        self.assertEqual(package["package_status"], "blocked")
        self.assertEqual(package["safety_checks"]["status"], "blocked")
        self.assertTrue(any(item["path"] == ".env" for item in package["excluded_paths"]))

    def test_whole_repo_request_is_blocked_until_narrowed(self) -> None:
        package = coffee_context_package.build_context_package(
            request_text="Send my whole repo to a model.",
            route_decision=self.route(),
            active_root=".",
            evidence_items=[],
        )

        self.assertEqual(package["package_status"], "blocked")
        self.assertEqual(package["safety_checks"]["status"], "blocked")
        self.assertTrue(any(item["path"] == "whole repository" for item in package["excluded_paths"]))

    def test_suspicious_text_is_labeled_without_exposing_value(self) -> None:
        suspicious_value = "Bearer " + ("x" * 32)
        package = coffee_context_package.build_context_package(
            request_text="Review this evidence",
            route_decision=self.route(),
            active_root=".",
            evidence_items=[self.evidence(snippet=f"Token was {suspicious_value}")],
        )

        snippet = package["evidence_items"][0]["snippet"]
        serialized = str(package)
        self.assertEqual(package["safety_checks"]["status"], "blocked")
        self.assertIn("Bearer token-like value", snippet)
        self.assertNotIn(suspicious_value, serialized)
        self.assertIn("Suspicious content detected", package["safety_checks"]["blocked_reasons"][0])

    def test_empty_evidence_package_still_builds(self) -> None:
        package = coffee_context_package.build_context_package(
            request_text="zzzz_unique_no_match_query",
            route_decision=self.route(),
            active_root=".",
            evidence_items=[],
        )

        self.assertEqual(package["package_status"], "preview_only")
        self.assertEqual(package["evidence_items"], [])
        self.assertEqual(package["safety_checks"]["status"], "passed")

    def test_produces_estimated_token_count(self) -> None:
        self.assertEqual(coffee_context_package.estimate_context_tokens("abcd"), 1)
        self.assertEqual(coffee_context_package.estimate_context_tokens("abcde"), 2)

    def test_produces_stable_summary(self) -> None:
        package = coffee_context_package.build_context_package(
            request_text="What is next?",
            route_decision=self.route(),
            active_root=".",
            evidence_items=[self.evidence()],
        )

        summary = coffee_context_package.summarize_context_package(package)

        self.assertEqual(summary["package_status"], "preview_only")
        self.assertEqual(summary["route_decision"], "Local evidence only")
        self.assertEqual(summary["evidence_item_count"], 1)
        self.assertEqual(summary["included_item_count"], 1)
        self.assertEqual(summary["approval_status"], "not_approved")

    def test_normalize_evidence_item_uses_expected_fields(self) -> None:
        item = coffee_context_package.normalize_evidence_item(self.evidence(), rank=1)

        self.assertEqual(item["path"], "brew-log/progress.md")
        self.assertEqual(item["title"], "Current shot")
        self.assertEqual(item["rank"], 1)
        self.assertTrue(item["included"])


if __name__ == "__main__":
    unittest.main()
