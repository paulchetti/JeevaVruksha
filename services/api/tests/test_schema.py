import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Attempt, Base, ClinicalCase, Membership, ProtocolPack, Tenant, User


class SchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_schema_contains_tenant_and_simulation_records(self) -> None:
        self.assertTrue(
            {
                "tenants",
                "users",
                "memberships",
                "subscriptions",
                "cohorts",
                "protocol_packs",
                "clinical_cases",
                "case_assignments",
                "attempts",
                "attempt_events",
                "badges",
                "user_badges",
                "invitations",
                "audit_logs",
            }.issubset(Base.metadata.tables)
        )

    def test_attempt_cannot_reference_case_from_another_tenant(self) -> None:
        tenant_a = Tenant(id="00000000-0000-0000-0000-000000000001", slug="college-a", name="A")
        tenant_b = Tenant(id="00000000-0000-0000-0000-000000000002", slug="college-b", name="B")
        user = User(
            id="00000000-0000-0000-0000-000000000003",
            oidc_issuer="https://issuer.example",
            oidc_subject="student-1",
        )
        membership = Membership(
            tenant_id=tenant_a.id,
            user_id=user.id,
            role="student",
        )
        pack = ProtocolPack(
            id="00000000-0000-0000-0000-000000000004",
            tenant_id=tenant_b.id,
            version="v1",
            title="Pack",
        )
        case = ClinicalCase(
            id="00000000-0000-0000-0000-000000000005",
            tenant_id=tenant_b.id,
            protocol_pack_id=pack.id,
            slug="case",
            case_version="v1",
            protocol_pack_version="v1",
            title="Case",
            specialty="Emergency medicine",
            duration_minutes=12,
        )
        self.session.add_all([tenant_a, tenant_b, user])
        self.session.flush()
        self.session.add(membership)
        self.session.flush()
        self.session.add(pack)
        self.session.flush()
        self.session.add(case)
        self.session.flush()

        attempt = Attempt(
            tenant_id=tenant_a.id,
            user_id=user.id,
            case_id=case.id,
            case_version="v1",
            protocol_pack_version="v1",
            idempotency_key="attempt-1",
        )
        self.session.add(attempt)
        with self.assertRaises(IntegrityError):
            self.session.flush()

    def test_unreviewed_protocol_pack_cannot_be_published(self) -> None:
        tenant = Tenant(
            id="00000000-0000-0000-0000-000000000006",
            slug="college-c",
            name="C",
        )
        self.session.add(tenant)
        self.session.flush()

        pack = ProtocolPack(
            tenant_id=tenant.id,
            version="v1",
            title="Pending pack",
            status="published",
            review_status="pending_local_review",
        )
        self.session.add(pack)
        with self.assertRaises(IntegrityError):
            self.session.flush()


if __name__ == "__main__":
    unittest.main()
