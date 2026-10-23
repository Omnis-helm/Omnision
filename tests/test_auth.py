import hashlib

from kpi_engine.auth import hash_password, verify_password, issue_token, verify_token, authenticate
from kpi_engine.data.models import UserClearance


def test_pbkdf2_and_legacy_hashes():
    h = hash_password("s3cret")
    assert h.startswith("pbkdf2_sha256$") and verify_password("s3cret", h) and not verify_password("nope", h)
    assert hash_password("s3cret") != h                         # salted
    legacy = hashlib.sha256(b"old").hexdigest()
    assert verify_password("old", legacy)


def test_default_users_authenticate():
    assert authenticate("admin", "adminpassword") == UserClearance.EXECUTIVE_VP
    assert authenticate("admin", "wrong") is None


def test_tokens_round_trip_and_tamper():
    tok = issue_token("engineer", UserClearance.SENIOR_ENGINEER)
    assert verify_token(tok) == ("engineer", UserClearance.SENIOR_ENGINEER)
    body, sig = tok.split(".")
    assert verify_token(body + "x." + sig) is None
    assert verify_token(issue_token("u", UserClearance.PUBLIC, ttl=-1)) is None
