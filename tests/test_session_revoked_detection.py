"""An account is dropped only when Telegram actually revoked the session.

A transient proxy or sqlite error must not be read as a revocation, so both
directions are asserted.
"""
import pytest
from telethon.errors import FloodWaitError, SessionRevokedError

from src.utils import is_session_revoked_error


class _FakeRequest:
    pass


REVOKED = [
    SessionRevokedError(_FakeRequest()),
    Exception("The authorization key is not registered in the system"),
    Exception("session was revoked"),
    Exception("user is not logged in"),
]

NOT_REVOKED = [
    ConnectionError("connection reset by peer"),
    TimeoutError("read timed out"),
    OSError("database is locked"),
    ValueError("phone number is invalid"),
    Exception("server returned 500"),
    # Regressions: each of these used to be read as a revocation because the
    # matcher looked for bare substrings like "session" or "authorization".
    OSError("unable to open database file: 989121234567.session"),
    ConnectionError("proxy authorization required"),
    TimeoutError("authorization pending"),
    Exception("failed to save session file"),
    OSError("no space left on device while writing session"),
]


@pytest.mark.parametrize('error', REVOKED, ids=lambda e: type(e).__name__ + ':' + str(e)[:30])
def test_revocation_is_detected(error):
    assert is_session_revoked_error(error) is True


@pytest.mark.parametrize('error', NOT_REVOKED, ids=lambda e: type(e).__name__ + ':' + str(e)[:30])
def test_transient_errors_are_not_revocations(error):
    assert is_session_revoked_error(error) is False, (
        f"{type(error).__name__}({error!r}) would wrongly drop a working account"
    )


def test_flood_wait_is_not_a_revocation():
    """Rate limiting is temporary; the account must survive it."""
    error = FloodWaitError(_FakeRequest())
    assert is_session_revoked_error(error) is False
