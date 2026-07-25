"""The argparse fallback used when click is missing must route every command."""
import types
from pathlib import Path

import pytest

CLI_SOURCE = Path(__file__).resolve().parent.parent / 'src' / 'cli.py'


@pytest.fixture(scope='module')
def fallback():
    source = CLI_SOURCE.read_text(encoding='utf-8').replace(
        '    import click\n', '    raise ImportError("click disabled for test")\n', 1)
    module = types.ModuleType('cli_fallback')
    exec(compile(source, str(CLI_SOURCE), 'exec'), module.__dict__)
    assert module.HAS_CLICK is False
    return module


class FakeManager:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self.calls[-1]
        return record


CASES = [
    (['list-accounts'], 'list_accounts'),
    (['add-account', '+989121234567'], 'add_account'),
    (['remove-account', 's1'], 'remove_account'),
    (['individual', 'reaction', 's1', 'L', '\U0001f44d'], 'reaction'),
    (['individual', 'vote', 's1', 'L', '2'], 'vote_poll'),
    (['individual', 'join', 's1', 'L'], 'join_chat'),
    (['individual', 'leave', 's1', 'L'], 'leave_chat'),
    (['individual', 'block', 's1', '@u'], 'block_user'),
    (['individual', 'send-pv', 's1', '@u', 'hi'], 'send_message'),
    (['individual', 'comment', 's1', 'L', 'text'], 'comment'),
    (['bulk', 'reaction', '3', 'L', '\U0001f44d'], 'bulk_operation'),
    (['bulk', 'vote', '3', 'L', '1'], 'bulk_operation'),
    (['bulk', 'join', '3', 'L'], 'bulk_operation'),
    (['bulk', 'leave', '3', 'L'], 'bulk_operation'),
    (['bulk', 'block', '3', '@u'], 'bulk_operation'),
    (['bulk', 'send-pv', '3', '@u', 'hi'], 'bulk_operation'),
    (['bulk', 'comment', '3', 'L', 'text'], 'bulk_operation'),
]


@pytest.mark.parametrize('argv,expected', CASES, ids=[' '.join(c[0]) for c in CASES])
def test_command_reaches_its_manager_method(fallback, argv, expected):
    args = fallback._build_parser().parse_args(argv)
    operation = fallback._resolve_operation(args)
    assert operation is not None, f"{argv} did not resolve to an operation"

    manager = FakeManager()
    operation(manager, args)

    assert manager.calls[0][0] == expected


@pytest.mark.parametrize('argv', [['bulk'], ['individual']])
def test_group_without_operation_resolves_to_nothing(fallback, argv):
    args = fallback._build_parser().parse_args(argv)
    assert fallback._resolve_operation(args) is None


def test_bulk_send_pv_passes_count_and_payload(fallback):
    args = fallback._build_parser().parse_args(['bulk', 'send-pv', '5', '@user', 'hello'])
    manager = FakeManager()
    fallback._resolve_operation(args)(manager, args)

    name, positional, keywords = manager.calls[0]
    assert positional == ('send_pv', 5)
    assert keywords == {'user_input': '@user', 'message': 'hello'}


def test_num_accounts_must_be_an_integer(fallback):
    with pytest.raises(SystemExit):
        fallback._build_parser().parse_args(['bulk', 'join', 'not-a-number', 'L'])
