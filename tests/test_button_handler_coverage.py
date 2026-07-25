"""Every keyboard button must be routable by callback_handler."""
import pytest

from src.handlers import CallbackHandler
from src.keyboards import Keyboard

KEYBOARDS = [
    'start_keyboard',
    'monitor_keyboard',
    'bulk_keyboard',
    'individual_keyboard',
    'report_keyboard',
]

UNRECOGNIZED_MARKERS = ('not recognized', 'شناسایی نشد')


def _button_data(keyboard):
    data = []
    for row in keyboard:
        for button in row:
            raw = getattr(button, 'data', None)
            if raw is None:
                continue
            data.append(raw.decode() if isinstance(raw, bytes) else raw)
    return data


def all_button_data():
    data = []
    for name in KEYBOARDS:
        data.extend(_button_data(getattr(Keyboard, name)()))
    return sorted(set(data))


def test_keyboards_expose_buttons():
    buttons = all_button_data()
    assert buttons, "no callback buttons found on any keyboard"
    assert len(buttons) >= len(KEYBOARDS)


@pytest.mark.parametrize('data', all_button_data())
@pytest.mark.asyncio
async def test_every_button_is_routable(data, mock_tbot, mock_callback_event):
    handler = CallbackHandler(mock_tbot)
    mock_callback_event.data = data.encode()

    await handler.callback_handler(mock_callback_event)

    replies = [
        str(call.args[0])
        for call in mock_callback_event.respond.call_args_list
        if call.args
    ]
    unroutable = [
        reply for reply in replies
        if any(marker in reply for marker in UNRECOGNIZED_MARKERS)
    ]
    assert not unroutable, f"button {data!r} has no handler: {unroutable}"


@pytest.mark.asyncio
async def test_unknown_button_is_rejected(mock_tbot, mock_callback_event):
    """The guard itself must work, otherwise the test above proves nothing."""
    handler = CallbackHandler(mock_tbot)
    mock_callback_event.data = b'no_such_button_xyz'

    await handler.callback_handler(mock_callback_event)

    replies = [
        str(call.args[0])
        for call in mock_callback_event.respond.call_args_list
        if call.args
    ]
    assert any(
        any(marker in reply for marker in UNRECOGNIZED_MARKERS)
        for reply in replies
    ), f"unknown callback data was silently accepted, replies={replies}"
