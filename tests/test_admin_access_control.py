"""Only the configured admin may drive the bot."""
import pytest

from src.Handlers import CallbackHandler
from src.utils import check_admin_access, validate_admin_id

ADMIN_ID = 123456789
NON_ADMIN_ID = 999999999


@pytest.mark.asyncio
async def test_admin_is_allowed(mock_event):
    mock_event.sender_id = ADMIN_ID
    assert await check_admin_access(mock_event, ADMIN_ID) is True


@pytest.mark.asyncio
async def test_non_admin_is_denied(mock_event):
    mock_event.sender_id = NON_ADMIN_ID
    assert await check_admin_access(mock_event, ADMIN_ID) is False


@pytest.mark.asyncio
async def test_unset_admin_id_fails_closed(mock_event, monkeypatch):
    """An unconfigured ADMIN_ID must deny everyone, not admit everyone."""
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    mock_event.sender_id = NON_ADMIN_ID
    assert await check_admin_access(mock_event, 0) is False


@pytest.mark.parametrize('bad', [None, 0, -1, 'abc', ''])
def test_invalid_admin_id_is_rejected(bad):
    with pytest.raises(ValueError):
        validate_admin_id(bad)


@pytest.mark.parametrize('value,expected', [(ADMIN_ID, ADMIN_ID), (str(ADMIN_ID), ADMIN_ID)])
def test_valid_admin_id_is_normalized(value, expected):
    assert validate_admin_id(value) == expected


@pytest.mark.asyncio
async def test_callback_from_non_admin_is_refused(mock_tbot, mock_callback_event, monkeypatch):
    monkeypatch.setattr('src.Handlers.ADMIN_ID', ADMIN_ID)
    handler = CallbackHandler(mock_tbot)
    mock_callback_event.sender_id = NON_ADMIN_ID
    mock_callback_event.data = b'add_account'

    await handler.callback_handler(mock_callback_event)

    replies = [str(c.args[0]) for c in mock_callback_event.respond.call_args_list if c.args]
    assert any('not the admin' in r for r in replies), replies
