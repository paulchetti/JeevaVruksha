import unittest

from app.simulation import Action, CaseSession, cardiac_arrest_case


class CaseSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = CaseSession.new(cardiac_arrest_case(), tenant_id="test-college")

    def test_action_prerequisite_is_enforced_without_recording_action(self) -> None:
        state = self.session.apply(Action(action_id="defibrillate"))

        self.assertIn("Attach defibrillator first.", state["message"])
        self.assertEqual(self.session.completed_actions, [])
        self.assertEqual(self.session.score, 0)
        self.assertEqual(self.session.events, [])

    def test_valid_action_updates_score_timeline_and_public_state(self) -> None:
        state = self.session.apply(
            Action(action_id="start-cpr", reasoning="Begin immediate resuscitation.")
        )

        self.assertEqual(state["score"], 30)
        self.assertEqual(state["completed_actions"], ["start-cpr"])
        self.assertEqual(len(state["timeline"]), 1)
        self.assertEqual(state["timeline"][0]["reasoning"], "Begin immediate resuscitation.")

    def test_duplicate_action_is_not_scored_twice(self) -> None:
        self.session.apply(Action(action_id="call-code"))
        state = self.session.apply(Action(action_id="call-code"))

        self.assertEqual(state["score"], 10)
        self.assertEqual(state["completed_actions"], ["call-code"])
        self.assertEqual(len(state["timeline"]), 1)
        self.assertEqual(state["message"], "Action already recorded.")

    def test_unsafe_action_is_recorded_with_warning_and_score_penalty(self) -> None:
        self.session.apply(Action(action_id="start-cpr"))
        state = self.session.apply(Action(action_id="order-ecg"))

        self.assertIn("delays immediate resuscitation", state["message"])
        self.assertEqual(state["score"], 25)
        self.assertIn("order-ecg", state["completed_actions"])

    def test_unknown_action_does_not_change_session(self) -> None:
        state = self.session.apply(Action(action_id="not-available"))

        self.assertEqual(state["message"], "Action is unavailable in this case.")
        self.assertEqual(self.session.completed_actions, [])
        self.assertEqual(self.session.score, 0)


if __name__ == "__main__":
    unittest.main()
