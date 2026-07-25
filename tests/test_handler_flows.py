"""Conversation-state routing.

Every state the bot can be put into must be routed by MessageHandler.
"""
import re
from pathlib import Path

import pytest

from src.Handlers import CONVERSATION_ROUTES, MessageHandler

SRC = Path(__file__).resolve().parent.parent / 'src'


def dispatcher_states():
    return sorted(CONVERSATION_ROUTES)


def armed_states():
    """States the rest of the codebase puts into _conversations."""
    states = set()
    for path in SRC.glob('*.py'):
        source = path.read_text(encoding='utf-8')
        states.update(re.findall(r"_conversations\[[^\]]*\]\s*=\s*'([a-z_]+)'", source))
        for call in re.findall(r'prompt_for_input\(.*?\)', source, re.S):
            states.update(re.findall(r"'([a-z_]+_handler)'", call))
    return sorted(states)


def _recorder():
    async def _noop(*args, **kwargs):
        return None
    return _noop


def test_states_were_discovered():
    """Guard the regexes themselves: an empty list must not pass silently."""
    assert len(dispatcher_states()) >= 15
    assert len(armed_states()) >= 5


@pytest.mark.parametrize('state', armed_states())
def test_every_armed_state_is_routable(state):
    assert state in dispatcher_states(), \
        f"conversation state {state!r} is set but message_handler never routes it"


@pytest.mark.parametrize('state', dispatcher_states())
@pytest.mark.asyncio
async def test_dispatcher_routes_state(state, mock_tbot, mock_new_message_event, monkeypatch):
    monkeypatch.setattr('src.Handlers.ADMIN_ID', mock_new_message_event.sender_id)
    handler = MessageHandler(mock_tbot)

    # Replace the concrete handlers so routing is measured, not their side effects.
    for owner in (handler.account_handler, handler.keyword_handler, handler.actions):
        for name in dir(owner):
            if name.endswith('_handler') and callable(getattr(owner, name, None)):
                monkeypatch.setattr(owner, name, _recorder(), raising=False)

    mock_tbot._conversations[mock_new_message_event.chat_id] = state
    mock_new_message_event.message.text = 'input'

    routed = await handler.message_handler(mock_new_message_event)

    assert routed is True, f"state {state!r} fell through message_handler"


@pytest.mark.asyncio
async def test_unknown_state_is_not_routed(mock_tbot, mock_new_message_event, monkeypatch):
    monkeypatch.setattr('src.Handlers.ADMIN_ID', mock_new_message_event.sender_id)
    handler = MessageHandler(mock_tbot)
    mock_tbot._conversations[mock_new_message_event.chat_id] = 'no_such_state_handler'
    mock_new_message_event.message.text = 'input'

    assert await handler.message_handler(mock_new_message_event) is False


@pytest.mark.asyncio
async def test_commands_are_not_swallowed(mock_tbot, mock_new_message_event, monkeypatch):
    """A /command must not be eaten by an armed conversation."""
    monkeypatch.setattr('src.Handlers.ADMIN_ID', mock_new_message_event.sender_id)
    handler = MessageHandler(mock_tbot)
    mock_tbot._conversations[mock_new_message_event.chat_id] = 'phone_number_handler'
    mock_new_message_event.message.text = '/start'

    assert await handler.message_handler(mock_new_message_event) is False
