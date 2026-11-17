import os
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient, PyJWKClientError
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .models import Membership, Subscription, Tenant, User


@dataclass(frozen=True)
class AuthContext:
    tenant_id: str
    user_id: str
    role: str


@lru_cache(maxsize=4)
def _engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def _unauthorized(detail: str = "Valid institutional sign-in is required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_access_token(token: str) -> dict:
    issuer = os.getenv("OIDC_ISSUER")
    audience = os.getenv("OIDC_AUDIENCE")
    jwks_url = os.getenv("OIDC_JWKS_URL")
    if not issuer or not audience or not jwks_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC authentication is not fully configured.",
        )

    try:
        key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iss", "sub", "aud"]},
        )
    except (jwt.PyJWTError, PyJWKClientError, OSError, TimeoutError) as error:
        raise _unauthorized() from error

    return claims


def resolve_membership(
    claims: dict, requested_tenant_id: str | None, database: Session
) -> AuthContext:
    user = database.scalar(
        select(User).where(
            User.oidc_issuer == claims["iss"],
            User.oidc_subject == claims["sub"],
            User.status == "active",
        )
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not enrolled. Access is invitation-only.",
        )

    memberships = database.execute(
        select(Membership, Tenant)
        .join(Tenant, Tenant.id == Membership.tenant_id)
        .where(Membership.user_id == user.id)
        .where(Membership.status == "active", Tenant.status == "active")
    ).all()

    if requested_tenant_id:
        try:
            tenant_id = str(UUID(requested_tenant_id))
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid institution context.") from error
        selected = next(
            (
                (membership, tenant)
                for membership, tenant in memberships
                if tenant.id == tenant_id
            ),
            None,
        )
    elif len(memberships) == 1:
        selected = memberships[0]
        tenant_id = selected[1].id
    elif len(memberships) > 1:
        raise HTTPException(
            status_code=400,
            detail="Select an institution before continuing.",
        )
    else:
        selected = None
        tenant_id = ""

    if selected is None and not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active membership exists for this institution.",
        )

    if selected is None:
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Select an institution before continuing.")
        tenant = database.scalar(
            select(Tenant).where(Tenant.id == tenant_id, Tenant.status == "active")
        )
        if tenant is None:
            raise HTTPException(status_code=404, detail="Institution not found.")
        role = "platform_admin"
    else:
        membership, tenant = selected
        role = membership.role

    now = datetime.now(timezone.utc)
    active_subscription = database.scalar(
        select(Subscription.id)
        .where(
            Subscription.tenant_id == tenant_id,
            Subscription.status.in_(("active", "trialing")),
            Subscription.starts_at <= now,
        )
        .where((Subscription.ends_at.is_(None)) | (Subscription.ends_at > now))
        .limit(1)
    )
    if active_subscription is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This institution does not have an active subscription.",
        )

    return AuthContext(tenant_id=tenant_id, user_id=user.id, role=role)


def get_auth_context(
    x_tenant_id: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> AuthContext:
    app_env = os.getenv("APP_ENV", "production").lower()
    auth_mode = os.getenv(
        "AUTH_MODE", "demo" if app_env in {"development", "test"} else "oidc"
    ).lower()

    if auth_mode == "demo":
        if app_env not in {"development", "test"}:
            raise HTTPException(
                status_code=503,
                detail="Demo authentication is only available in development.",
            )
        if not x_tenant_id:
            raise _unauthorized("Institution identity is required.")
        return AuthContext(tenant_id=x_tenant_id, user_id="demo-user", role="college_admin")

    if auth_mode != "oidc":
        raise HTTPException(status_code=503, detail="Unsupported authentication mode.")
    if not authorization:
        raise _unauthorized()
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token.strip():
        raise _unauthorized()

    claims = _decode_access_token(token.strip())
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=503,
            detail="Database access is not configured for institutional sign-in.",
        )

    with Session(_engine(database_url)) as database:
        return resolve_membership(claims, x_tenant_id, database)
