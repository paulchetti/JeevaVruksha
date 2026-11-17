import unittest

from fastapi import HTTPException

from app.auth import AuthContext
from app.main import ActionRequest, record_action, start_attempt
from app.simulation import cardiac_arrest_case


class TenantIsolationTests(unittest.TestCase):
    def test_attempt_cannot_be_accessed_by_another_tenant(self) -> None:
        case = cardiac_arrest_case()
        context = AuthContext(
            tenant_id="college-a", user_id="student-a", role="student"
        )
        attempt = start_attempt(case.id, context=context)

        with self.assertRaises(HTTPException) as error:
            record_action(
                attempt["attempt_id"],
                ActionRequest(action_id="call-code"),
                context=AuthContext(
                    tenant_id="college-b", user_id="student-b", role="student"
                ),
            )

        self.assertEqual(error.exception.status_code, 404)

    def test_attempt_owner_can_record_action(self) -> None:
        case = cardiac_arrest_case()
        context = AuthContext(
            tenant_id="college-a", user_id="student-a", role="student"
        )
        attempt = start_attempt(case.id, context=context)

        state = record_action(
            attempt["attempt_id"],
            ActionRequest(action_id="call-code"),
            context=context,
        )

        self.assertEqual(state["score"], 10)

    def test_missing_tenant_is_rejected(self) -> None:
        from app.auth import get_auth_context

        with self.assertRaises(HTTPException) as error:
            get_auth_context(x_tenant_id=None, authorization=None)

        self.assertEqual(error.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
