"""Bulk "Send PV" asks how many accounts to use before doing anything."""
import pytest

from src.Handlers import CallbackHandler


def _replies(event):
    return [str(c.args[0]) for c in event.respond.call_args_list if c.args]


@pytest.mark.asyncio
async def test_prompt_reports_available_account_count(mock_tbot, mock_callback_event):
    mock_tbot.active_clients = {'989121111111': object(), '989122222222': object()}
    handler = CallbackHandler(mock_tbot)

    await handler.handle_bulk_send_pv(mock_callback_event)

    replies = _replies(mock_callback_event)
    assert replies, "handler sent no prompt"
    assert '2 accounts available' in replies[0]
    assert 'between 1 and 2' in replies[0]


@pytest.mark.asyncio
async def test_conversation_state_is_armed(mock_tbot, mock_callback_event):
    mock_tbot.active_clients = {'989121111111': object()}
    handler = CallbackHandler(mock_tbot)

    await handler.handle_bulk_send_pv(mock_callback_event)

    assert mock_tbot._conversations.get(mock_callback_event.chat_id) == \
        'bulk_send_pv_account_count_handler'


@pytest.mark.asyncio
async def test_no_accounts_short_circuits(mock_tbot, mock_callback_event):
    mock_tbot.active_clients = {}
    handler = CallbackHandler(mock_tbot)

    await handler.handle_bulk_send_pv(mock_callback_event)

    replies = _replies(mock_callback_event)
    assert any('No accounts available' in r for r in replies), replies
    assert mock_callback_event.chat_id not in mock_tbot._conversations, \
        "conversation was armed even though there is nothing to send with"
