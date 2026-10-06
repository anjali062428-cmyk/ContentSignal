"""
Comprehensive Unit & Integration Test Suite for Clerk Authentication & Tenant Isolation.
Covers:
- Unauthenticated request rejected (401)
- Valid Clerk-authenticated request accepted (200)
- Invalid token rejected (401)
- Expired session rejected (401)
- Authenticated user identity correctly resolved to ContentSignal user record with clerk_user_id
- Tenant isolation: User A cannot access or delete User B's resources (403)
- Public routes remain accessible without authentication (200)
- Existing ContentSignal core functionality (opportunities, priority queue) still works
"""
import time
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import jwt

from backend.main import app
from backend.database import SessionLocal
from backend.models import User, Dataset, Page, Opportunity
from backend.clerk_auth import get_or_create_clerk_user, verify_clerk_token

client = TestClient(app)

# Generate an in-memory RSA keypair for real RS256 cryptographic token tests
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_private_pem = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode("utf-8")

_public_key = _private_key.public_key()
_public_pem = _public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode("utf-8")


def generate_test_clerk_token(
    sub: str,
    email: str = None,
    name: str = None,
    expired: bool = False,
    invalid_signature: bool = False,
) -> str:
    """Generates a real RS256 signed Clerk session token."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "iss": "https://clerk.contentsignal.ai",
        "iat": now - 60,
        "exp": (now - 10) if expired else (now + 3600),
        "nbf": now - 60,
    }
    if email:
        payload["email"] = email
        payload["primary_email_address"] = email
    if name:
        payload["full_name"] = name

    signing_key = _private_pem
    if invalid_signature:
        # Sign with a completely different throwaway key
        alt_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        signing_key = alt_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

    return jwt.encode(payload, signing_key, algorithm="RS256", headers={"kid": "test_clerk_key_1"})


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_unauthenticated_request_rejected_on_protected_route():
    """Protected endpoints must reject requests with no token with HTTP 401."""
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_invalid_clerk_token_rejected():
    """Tokens with invalid signatures or corrupt format must return HTTP 401."""
    with patch("backend.clerk_auth.CLERK_JWT_KEY", _public_pem):
        # 1. Random garbage token
        res_bad = client.get("/api/auth/me", headers={"Authorization": "Bearer not_a_valid_jwt_token"})
        assert res_bad.status_code == 401

        # 2. RS256 token signed by an unauthorized/untrusted key
        bad_sig_token = generate_test_clerk_token("user_attacker_1", invalid_signature=True)
        res_untrusted = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_sig_token}"})
        assert res_untrusted.status_code == 401


def test_expired_clerk_session_rejected():
    """Expired Clerk session tokens must be rejected with HTTP 401."""
    with patch("backend.clerk_auth.CLERK_JWT_KEY", _public_pem):
        expired_token = generate_test_clerk_token("user_expired_1", expired=True)
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert res.status_code == 401
        assert "expired" in res.json()["detail"].lower()


def test_valid_clerk_authenticated_request_accepted(db_session):
    """Valid Clerk RS256 session token is accepted and returns 200 OK."""
    clerk_id = f"user_clerk_{uuid.uuid4().hex[:10]}"
    email = f"{clerk_id}@example.com"
    token = generate_test_clerk_token(clerk_id, email=email, name="Clerk User")

    with patch("backend.clerk_auth.CLERK_JWT_KEY", _public_pem):
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["clerk_user_id"] == clerk_id
        assert data["email"] == email
        assert data["is_active"] is True


def test_authenticated_user_identity_correctly_resolved(db_session):
    """
    Verifies that the Clerk user identity (sub) is persisted as clerk_user_id
    and reused on subsequent requests without duplication.
    """
    clerk_id = f"user_clerk_{uuid.uuid4().hex[:10]}"
    email = f"resolve_{uuid.uuid4().hex[:8]}@example.com"
    token = generate_test_clerk_token(clerk_id, email=email, name="Resolved User")

    with patch("backend.clerk_auth.CLERK_JWT_KEY", _public_pem):
        # 1. First request provisions the user
        res1 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res1.status_code == 200
        user_id_1 = res1.json()["id"]

        # 2. Database record exists and has clerk_user_id as stable external identity
        user_record = db_session.query(User).filter(User.clerk_user_id == clerk_id).first()
        assert user_record is not None
        assert user_record.id == user_id_1
        assert user_record.email == email

        # 3. Second request reuses the same database record
        res2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res2.status_code == 200
        assert res2.json()["id"] == user_id_1

        # Count records to ensure no duplicates
        total_matching = db_session.query(User).filter(User.clerk_user_id == clerk_id).count()
        assert total_matching == 1


def test_tenant_isolation_user_a_cannot_access_or_delete_user_b_dataset(db_session):
    """
    Multi-User Authorization Security:
    - User A creates a dataset.
    - User B cannot read, analyze, or delete User A's dataset.
    - Returns HTTP 403 Forbidden.
    """
    user_a_clerk_id = f"user_clerk_a_{uuid.uuid4().hex[:8]}"
    user_b_clerk_id = f"user_clerk_b_{uuid.uuid4().hex[:8]}"

    token_a = generate_test_clerk_token(user_a_clerk_id, email="usera@example.com", name="User A")
    token_b = generate_test_clerk_token(user_b_clerk_id, email="userb@example.com", name="User B")

    with patch("backend.clerk_auth.CLERK_JWT_KEY", _public_pem):
        # 1. User A authenticates
        res_a = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"})
        assert res_a.status_code == 200
        user_a_db_id = res_a.json()["id"]

        # 2. Create private dataset owned by User A
        private_ds_id = f"ds_priv_{uuid.uuid4().hex[:8]}"
        priv_ds = Dataset(
            dataset_id=private_ds_id,
            name="User A Confidential Dataset",
            user_id=user_a_db_id,
            is_starter=False,
            row_count=100,
            column_count=10,
            validation_status="valid",
        )
        db_session.add(priv_ds)
        db_session.commit()

        # 3. User A can view their own dataset
        res_a_view = client.get(f"/api/datasets/{private_ds_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert res_a_view.status_code == 200
        assert res_a_view.json()["dataset_id"] == private_ds_id

        # 4. User B attempts to access User A's dataset -> 403 Forbidden
        res_b_view = client.get(f"/api/datasets/{private_ds_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert res_b_view.status_code == 403
        assert "Access denied" in res_b_view.json()["detail"]

        # 5. User B attempts to trigger an analysis job on User A's dataset -> 403 Forbidden
        res_b_job = client.post(f"/api/datasets/{private_ds_id}/jobs", headers={"Authorization": f"Bearer {token_b}"})
        assert res_b_job.status_code == 403

        # 6. User B attempts to delete User A's dataset -> 403 Forbidden
        res_b_del = client.delete(f"/api/datasets/{private_ds_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert res_b_del.status_code == 403
        assert "Access denied" in res_b_del.json()["detail"]

        # 7. Dataset still safely exists in database
        check_ds = db_session.query(Dataset).filter(Dataset.dataset_id == private_ds_id).first()
        assert check_ds is not None

        # 8. User A can safely delete their own dataset
        res_a_del = client.delete(f"/api/datasets/{private_ds_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert res_a_del.status_code == 200
        assert res_a_del.json()["status"] == "deleted"


def test_public_routes_remain_accessible_without_auth():
    """Public endpoints must remain accessible without any Authorization headers."""
    # Health checks
    assert client.get("/api/health").status_code == 200
    assert client.get("/health").status_code == 200

    # Diagnostics
    assert client.get("/api/auth/email-status").status_code == 200

    # Public starter dataset overview & priorities
    assert client.get("/api/overview").status_code == 200
    assert client.get("/api/opportunities?page=1&page_size=5").status_code == 200


def test_existing_contentsignal_functionality_works_with_clerk():
    """Verify that ContentSignal opportunities and data pipelines work seamlessly with Clerk auth."""
    clerk_id = f"user_clerk_ops_{uuid.uuid4().hex[:8]}"
    token = generate_test_clerk_token(clerk_id, email="ops@contentsignal.ai", name="Operations Lead")

    with patch("backend.clerk_auth.CLERK_JWT_KEY", _public_pem):
        # 1. User accesses overview KPIs
        res_ov = client.get("/api/overview", headers={"Authorization": f"Bearer {token}"})
        assert res_ov.status_code == 200
        assert res_ov.json()["total_pages_analyzed"] >= 1000

        # 2. User accesses priority opportunities queue
        res_opp = client.get("/api/opportunities?page=1&page_size=5", headers={"Authorization": f"Bearer {token}"})
        assert res_opp.status_code == 200
        items = res_opp.json()["items"]
        assert len(items) > 0

        # 3. User accesses starter dataset
        res_ds = client.get("/api/datasets/starter-flyrank", headers={"Authorization": f"Bearer {token}"})
        assert res_ds.status_code == 200
        assert res_ds.json()["is_starter"] is True
