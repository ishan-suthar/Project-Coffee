import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from router.app.config import Settings
from router.app.system_prompt import (
    IDENTITY_MESSAGE,
    build_date_system_message,
    build_identity_system_message,
    build_system_message,
)


class BuildDateSystemMessageTests(unittest.TestCase):
    def test_none_when_disabled(self):
        settings = Settings(system_prompt_include_date=False)
        self.assertIsNone(build_date_system_message(settings))

    def test_default_local_timezone_uses_utc_offset_label_not_abbreviation(self):
        settings = Settings()  # system_prompt_include_date=True, timezone="local"
        message = build_date_system_message(settings)
        self.assertIsNotNone(message)

        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        self.assertIn(f"Today's date is {today}", message)
        self.assertIn("UTC", message)
        # A bare abbreviation like "CST"/"EST" is genuinely ambiguous
        # (US Central Standard Time vs. China Standard Time) - the label
        # must always be an explicit numeric UTC offset.
        self.assertRegex(message, r"UTC[+-]\d{2}:\d{2}")

    def test_explicit_iana_timezone_used_for_the_date_and_named_in_the_label(self):
        settings = Settings(system_prompt_timezone="America/Chicago")
        message = build_date_system_message(settings)

        expected_date = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d")
        self.assertIn(f"Today's date is {expected_date}", message)
        self.assertIn("America/Chicago", message)
        self.assertRegex(message, r"UTC[+-]\d{2}:\d{2}")

    def test_unrecognized_timezone_name_falls_back_to_local_rather_than_raising(self):
        settings = Settings(system_prompt_timezone="Not/A_Real_Zone")
        message = build_date_system_message(settings)  # must not raise

        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        self.assertIn(f"Today's date is {today}", message)

    def test_timezone_setting_is_case_insensitive_for_the_local_sentinel(self):
        settings = Settings(system_prompt_timezone="Local")
        message = build_date_system_message(settings)
        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        self.assertIn(f"Today's date is {today}", message)

    def test_message_is_short_one_or_two_sentences(self):
        """This rides on every /v1/order request and every token is
        billed - keep it terse."""

        settings = Settings()
        message = build_date_system_message(settings)
        self.assertLessEqual(len(message), 200)
        self.assertLessEqual(message.count(". ") + message.count(" - "), 2)


class BuildIdentitySystemMessageTests(unittest.TestCase):
    def test_none_when_disabled(self):
        settings = Settings(system_prompt_include_identity=False)
        self.assertIsNone(build_identity_system_message(settings))

    def test_present_by_default_and_states_the_facts_it_exists_to_state(self):
        settings = Settings()  # system_prompt_include_identity defaults True
        message = build_identity_system_message(settings)
        self.assertIsNotNone(message)

        self.assertIn("Project Coffee", message)
        self.assertIn("Ishan Suthar", message)
        self.assertIn("Bean", message)
        self.assertIn("Ledger", message)
        self.assertIn("Pantry", message)

    def test_message_stays_under_the_per_request_character_budget(self):
        """This rides on every /v1/order request and every character is
        billed. 400 is the agreed ceiling (Brew 56); the text is ~336, so
        this has real headroom but will fail loudly if someone grows the
        block into a paragraph."""

        self.assertLessEqual(len(IDENTITY_MESSAGE), 400)

    def test_message_is_ascii_only(self):
        """Goes out over the wire to arbitrary providers - no em dashes or
        smart quotes, matching the date sentence's convention."""

        IDENTITY_MESSAGE.encode("ascii")  # raises UnicodeEncodeError if not


class BuildSystemMessageCompositionTests(unittest.TestCase):
    """All four on/off combinations of the two independently-gated parts.
    The contract is that they compose into ONE message, never two."""

    def test_both_on_composes_one_message_identity_first_then_date(self):
        settings = Settings(
            system_prompt_include_identity=True, system_prompt_include_date=True
        )
        message = build_system_message(settings)

        self.assertIn("Project Coffee", message)
        self.assertIn("Today's date is", message)
        # Identity leads: it is a fixed constant while the date changes
        # daily, so the stable part goes first (longest common prefix).
        self.assertLess(message.index("Project Coffee"), message.index("Today's date is"))
        self.assertIn("\n\n", message)
        # Exactly one blank-line join between exactly two parts.
        self.assertEqual(len(message.split("\n\n")), 2)

    def test_identity_only(self):
        settings = Settings(
            system_prompt_include_identity=True, system_prompt_include_date=False
        )
        message = build_system_message(settings)

        self.assertEqual(message, IDENTITY_MESSAGE)
        self.assertNotIn("Today's date is", message)

    def test_date_only_is_byte_identical_to_the_date_message_alone(self):
        """Brew 53's behaviour must survive Brew 56 exactly - turning
        identity off has to leave the date path untouched, not merely
        similar."""

        settings = Settings(
            system_prompt_include_identity=False, system_prompt_include_date=True
        )
        self.assertEqual(
            build_system_message(settings), build_date_system_message(settings)
        )

    def test_both_off_returns_none(self):
        settings = Settings(
            system_prompt_include_identity=False, system_prompt_include_date=False
        )
        self.assertIsNone(build_system_message(settings))

    def test_the_two_settings_are_independent(self):
        """Neither gate may imply the other - a regression here would show
        up as one toggle silently controlling both."""

        identity_only = Settings(
            system_prompt_include_identity=True, system_prompt_include_date=False
        )
        date_only = Settings(
            system_prompt_include_identity=False, system_prompt_include_date=True
        )
        self.assertIsNotNone(build_system_message(identity_only))
        self.assertIsNotNone(build_system_message(date_only))
        self.assertNotEqual(
            build_system_message(identity_only), build_system_message(date_only)
        )


if __name__ == "__main__":
    unittest.main()
