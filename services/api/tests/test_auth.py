import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app import auth
from app.models import Base, Membership, Subscription, Tenant, User


class AuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.database = Session(self.engine)
        self.tenant_id = "00000000-0000-0000-0000-000000000101"
        self.user_id = "00000000-0000-0000-0000-000000000102"
        self.issuer = "https://issuer.example"
        self.claims = {"iss": self.issuer, "sub": "student-1"}
        now = datetime.now(timezone.utc)
        self.database.add_all(
            [
                Tenant(id=self.tenant_id, slug="college-a", name="College A"),
                User(
                    id=self.user_id,
                    oidc_issuer=self.issuer,
                    oidc_subject="student-1",
                ),
            ]
        )
        self.database.flush()
        self.database.add(
            Membership(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                role="student",
            )
        )
        self.database.add(
            Subscription(
                tenant_id=self.tenant_id,
                plan_code="institution",
                status="active",
                starts_at=now - timedelta(days=1),
            )
        )
        self.database.commit()

    def tearDown(self) -> None:
        self.database.close()
        self.engine.dispose()

    def test_active_oidc_membership_and_subscription_resolve_context(self) -> None:
        context = auth.resolve_membership(self.claims, None, self.database)

        self.assertEqual(context.tenant_id, self.tenant_id)
        self.assertEqual(context.user_id, self.user_id)
        self.assertEqual(context.role, "student")

    def test_user_cannot_select_another_tenant(self) -> None:
        other_tenant_id = "00000000-0000-0000-0000-000000000103"
        self.database.add(
            Tenant(id=other_tenant_id, slug="college-b", name="College B")
        )
        self.database.commit()

        with self.assertRaises(HTTPException) as error:
            auth.resolve_membership(self.claims, other_tenant_id, self.database)

        self.assertEqual(error.exception.status_code, 403)

    def test_inactive_subscription_blocks_access(self) -> None:
        subscription = self.database.query(Subscription).one()
        subscription.status = "canceled"
        self.database.commit()

        with self.assertRaises(HTTPException) as error:
            auth.resolve_membership(self.claims, self.tenant_id, self.database)

        self.assertEqual(error.exception.status_code, 403)

    def test_unknown_oidc_identity_is_invitation_only(self) -> None:
        claims = {"iss": self.issuer, "sub": "not-invited"}

        with self.assertRaises(HTTPException) as error:
            auth.resolve_membership(claims, self.tenant_id, self.database)

        self.assertEqual(error.exception.status_code, 403)
        self.assertIn("invitation-only", error.exception.detail)

    def test_demo_mode_is_refused_outside_development(self) -> None:
        with patch.dict(
            os.environ, {"APP_ENV": "production", "AUTH_MODE": "demo"}
        ):
            with self.assertRaises(HTTPException) as error:
                auth.get_auth_context("college-a", None)

        self.assertEqual(error.exception.status_code, 503)

    def test_missing_environment_defaults_to_oidc_not_demo(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as error:
                auth.get_auth_context(self.tenant_id, None)

        self.assertEqual(error.exception.status_code, 401)

    def test_oidc_signature_and_claims_are_verified(self) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        token = jwt.encode(
            {
                "iss": self.issuer,
                "sub": "student-1",
                "aud": "jeeva-api",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
                "iat": datetime.now(timezone.utc),
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )
        fake_jwks = SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=public_key)
        )
        with (
            patch.dict(
                os.environ,
                {
                    "OIDC_ISSUER": self.issuer,
                    "OIDC_AUDIENCE": "jeeva-api",
                    "OIDC_JWKS_URL": "https://issuer.example/jwks",
                },
            ),
            patch.object(auth, "_jwks_client", return_value=fake_jwks),
        ):
            claims = auth._decode_access_token(token)

        self.assertEqual(claims["sub"], "student-1")
