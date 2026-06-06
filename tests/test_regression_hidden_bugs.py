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


# ===========================================================================
# Pass 3 — deeper bugs (config store, env parsing, markdown, UI labels, routing)
# ===========================================================================
import json
from telethon.tl.types import User, Channel

from src.Config import ConfigManager, get_env_int
from src.Keyboards import Keyboard
from src.Monitor import Monitor


class TestConfigStore:
    def test_configmanager_defaults_to_clients_json(self):
        # CLI and bot must share the same store; default must not be config.json
        assert ConfigManager.__init__.__defaults__[0] == "clients.json"

    def test_save_config_is_atomic_and_leaves_no_temp(self, tmp_path):
        path = tmp_path / "clients.json"
        cm = ConfigManager(str(path))
        cm.save_config({"clients": {"a": []}, "KEYWORDS": ["x"]})

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["clients"] == {"a": []}
        assert data["KEYWORDS"] == ["x"]
        # the atomic temp file must be cleaned up
        assert list(tmp_path.glob("*.tmp")) == []


class TestEnvIntParsing:
    def test_zero_is_honoured(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_SLEEP", "0")
        assert get_env_int("RATE_LIMIT_SLEEP", default=60) == 0

    def test_whitespace_zero_is_honoured(self, monkeypatch):
        monkeypatch.setenv("GROUPS_BATCH_SIZE", " 0 ")
        assert get_env_int("GROUPS_BATCH_SIZE", default=10) == 0

    def test_placeholder_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("API_ID", "your_api_id_here")
        assert get_env_int("API_ID", default=0) == 0

    def test_empty_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_SLEEP", "")
        assert get_env_int("RATE_LIMIT_SLEEP", default=60) == 60


class TestToggleLabel:
    def test_inactive_account_shows_enable(self):
        rows = Keyboard.toggle_and_delete_keyboard("Inactive", "sess")
        assert rows[0][0].text.endswith("Enable")

    def test_inactive_auth_error_shows_enable(self):
        rows = Keyboard.toggle_and_delete_keyboard("Inactive (Auth Error)", "sess")
        assert rows[0][0].text.endswith("Enable")

    def test_active_account_shows_disable(self):
        rows = Keyboard.toggle_and_delete_keyboard("Active", "sess")
        assert rows[0][0].text.endswith("Disable")


@pytest.mark.asyncio
class TestCallbackRoutingNoFanOut:
    async def test_individual_action_on_missing_account_does_not_fan_out(self, mock_tbot, mock_callback_event):
        from src.Handlers import CallbackHandler
        mock_tbot.active_clients = {}
        handler = CallbackHandler(mock_tbot)
        handler.actions.handle_group_action = AsyncMock()

        # digit-only suffix is a phone-shaped session key whose account is gone;
        # it must NOT be reinterpreted as a bulk count of ~10^11 accounts.
        mock_callback_event.data = b"reaction_989121234567"
        await handler.callback_handler(mock_callback_event)

        handler.actions.handle_group_action.assert_not_called()
        mock_callback_event.respond.assert_awaited()


@pytest.mark.asyncio
class TestStartClearsState:
    async def test_start_command_clears_conversation_state(self, mock_tbot, mock_event):
        from src.Handlers import CommandHandler
        mock_event.chat_id = 555
        mock_event.sender_id = 999
        mock_tbot._conversations = {555: "poll_link_handler"}

        handler = CommandHandler(mock_tbot)
        with patch("src.utils.validate_admin_id", return_value=999):
            await handler.start_command(mock_event)

        assert 555 not in mock_tbot._conversations
        mock_event.respond.assert_awaited()


@pytest.mark.asyncio
class TestMonitorMarkdownSafe:
    async def test_message_with_markdown_chars_is_still_forwarded(self, mock_tbot, mock_new_message_event, mock_telegram_client):
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        mock_tbot.config = {"KEYWORDS": ["test"], "IGNORE_USERS": []}
        mock_tbot.tbot.send_message = AsyncMock()

        # content with unbalanced markdown that would break default parse mode
        mock_new_message_event.message.text = "test *bold _italic [link `code"
        mock_new_message_event.chat_id = -1001234567890
        mock_new_message_event.out = False
        mock_new_message_event.id = 7

        sender = Mock(spec=User)
        sender.id = 987654321
        sender.first_name = "A*B"
        sender.last_name = "C_D"
        mock_new_message_event.get_sender = AsyncMock(return_value=sender)

        chat = Mock(spec=Channel)
        chat.id = -1001234567890
        chat.title = "Chat[1]"
        chat.username = "testchannel"
        mock_new_message_event.get_chat = AsyncMock(return_value=chat)

        handler = await monitor.process_messages_for_client(mock_telegram_client)
        await handler(mock_new_message_event)

        # must be forwarded (not silently dropped) and sent literally.
        mock_tbot.tbot.send_message.assert_called_once()
        kwargs = mock_tbot.tbot.send_message.call_args.kwargs
        # parse_mode must be EXPLICITLY disabled (key present), not merely absent,
        # so user markdown can't break the real send and drop the message.
        assert "parse_mode" in kwargs and kwargs["parse_mode"] is None
        sent_text = mock_tbot.tbot.send_message.call_args[0][1]
        assert "*bold" in sent_text  # user content preserved verbatim
