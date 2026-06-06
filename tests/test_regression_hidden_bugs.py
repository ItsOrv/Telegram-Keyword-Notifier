"""
Regression tests for hidden bugs found during the deep debugging pass.

Each test documents a specific bug that was fixed and guards against it
reappearing. Test names reference the symptom, not the implementation.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from telethon import TelegramClient

from src.Validation import InputValidator
from src.actions import Actions
from src.utils import remove_revoked_session_completely


# ---------------------------------------------------------------------------
# Validation: modern '+' invite links must be accepted
# ---------------------------------------------------------------------------
class TestInviteLinkValidation:
    @pytest.mark.parametrize("link", [
        "https://t.me/+AbCdEf123",
        "http://t.me/+AbCdEf123",
        "t.me/+AbCdEf123",
        "https://t.me/joinchat/AbCdEf",
        "https://t.me/durov",
        "https://t.me/c/123/456",
    ])
    def test_valid_links_accepted(self, link):
        is_valid, error = InputValidator.validate_telegram_link(link)
        assert is_valid is True, f"{link!r} should be valid, got: {error}"

    @pytest.mark.parametrize("link", ["", "   ", "https://example.com/foo"])
    def test_invalid_links_rejected(self, link):
        is_valid, _ = InputValidator.validate_telegram_link(link)
        assert is_valid is False


# ---------------------------------------------------------------------------
# parse_telegram_link: the message id is the LAST segment (topic/comment links)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestParseTelegramLinkLastSegment:
    async def test_private_two_segment(self, mock_tbot):
        actions = Actions(mock_tbot)
        result = actions._parse_private_channel_link("https://t.me/c/1234567/789")
        assert result == (int("-1001234567"), 789)

    async def test_private_topic_link_uses_last_segment(self, mock_tbot):
        actions = Actions(mock_tbot)
        # t.me/c/<chat>/<topic>/<msg> -> message id is 45, NOT the topic id 2
        result = actions._parse_private_channel_link("https://t.me/c/1234567/2/45")
        assert result == (int("-1001234567"), 45)

    async def test_public_topic_link_uses_last_segment(self, mock_tbot):
        actions = Actions(mock_tbot)
        entity, message_id = await actions._parse_public_channel_link("t.me/durov/2/45")
        assert entity == "durov"
        assert message_id == 45


# ---------------------------------------------------------------------------
# remove_revoked_session_completely: must resolve the '.session' filename form
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestRevokedSessionRemoval:
    async def test_removal_by_session_filename(self, mock_tbot):
        client = AsyncMock(spec=TelegramClient)
        client.disconnect = AsyncMock()
        client.session = MagicMock()
        client.session.filename = "foo.session"

        mock_tbot.active_clients = {"foo": client}
        mock_tbot.config = {"clients": {"foo": []}, "inactive_accounts": {}}

        # Caller passes the Telethon filename, dict key is the bare 'foo'
        await remove_revoked_session_completely(mock_tbot, "foo.session")

        assert "foo" not in mock_tbot.active_clients
        assert "foo" not in mock_tbot.config["clients"]
        client.disconnect.assert_awaited_once()


# ---------------------------------------------------------------------------
# _remove_revoked_sessions: must not deadlock on the non-reentrant lock
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestRemoveRevokedSessionsNoDeadlock:
    async def test_completes_without_deadlock(self, mock_tbot):
        client = AsyncMock(spec=TelegramClient)
        client.disconnect = AsyncMock()
        client.session = MagicMock()
        client.session.filename = "foo.session"

        mock_tbot.active_clients = {"foo": client}
        mock_tbot.config = {"clients": {"foo": []}, "inactive_accounts": {}}

        actions = Actions(mock_tbot)
        # Before the fix this re-acquired active_clients_lock and hung forever.
        await asyncio.wait_for(actions._remove_revoked_sessions(["foo"]), timeout=5)

        assert "foo" not in mock_tbot.active_clients


# ---------------------------------------------------------------------------
# Poll vote: must send the answer's creator-defined option bytes, not the index
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestPollVoteOptionBytes:
    async def test_individual_vote_sends_answer_bytes(self, mock_tbot, mock_event):
        actions = Actions(mock_tbot)

        account = AsyncMock(spec=TelegramClient)
        account.is_connected = Mock(return_value=True)
        account.session = MagicMock()
        account.session.filename = "acct.session"
        account.get_entity = AsyncMock(return_value=MagicMock())

        # Poll with two answers carrying distinct, non-index option bytes
        message = MagicMock()
        message.poll = MagicMock()
        message.poll.poll.answers = [
            SimpleNamespace(option=b"\xaa"),
            SimpleNamespace(option=b"\xbb"),
        ]
        account.get_messages = AsyncMock(return_value=message)

        # option index 1 (0-based) -> must send b"\xbb"
        await actions._execute_individual_poll_vote(
            mock_event, account, "https://t.me/c/1234567/45", 1, 2
        )

        assert account.call_args is not None, "SendVoteRequest was never sent"
        sent_request = account.call_args[0][0]
        assert sent_request.options == [b"\xbb"]

    async def test_individual_vote_rejects_out_of_range_option(self, mock_tbot, mock_event):
        actions = Actions(mock_tbot)

        account = AsyncMock(spec=TelegramClient)
        account.is_connected = Mock(return_value=True)
        account.session = MagicMock()
        account.session.filename = "acct.session"
        account.get_entity = AsyncMock(return_value=MagicMock())

        message = MagicMock()
        message.poll = MagicMock()
        message.poll.poll.answers = [SimpleNamespace(option=b"\xaa")]
        account.get_messages = AsyncMock(return_value=message)

        # option index 5 on a 1-answer poll -> no vote sent, user gets an error
        await actions._execute_individual_poll_vote(
            mock_event, account, "https://t.me/c/1234567/45", 5, 6
        )

        account.assert_not_called()
        mock_event.respond.assert_awaited()


# ---------------------------------------------------------------------------
# SessionManager wiring: detect_sessions must work when given the bot wrapper
# (regression for passing the raw client instead of the wrapper)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestSessionManagerWiring:
    async def test_detect_sessions_loads_with_wrapper(self, mock_tbot):
        from src.Client import SessionManager

        mock_tbot.config = {"clients": {"acct1": []}}
        mock_tbot.active_clients = {}

        manager = SessionManager(mock_tbot.config, mock_tbot.active_clients, mock_tbot)

        with patch("src.Client.TelegramClient", return_value=MagicMock()):
            await manager.detect_sessions()

        # If the wrapper (with active_clients_lock) is wired correctly, the
        # session is loaded; the old bug raised RuntimeError and loaded nothing.
        assert "acct1" in mock_tbot.active_clients
