"""LOCAL_AI_DISABLED_REASON: while set, nothing may open a connection to Ollama."""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'apps' / 'api'))
import ai_gateway as gw  # noqa: E402
import local_ai  # noqa: E402
import model_identity as mi  # noqa: E402


@pytest.fixture
def disabled(monkeypatch):
    monkeypatch.setenv('LOCAL_AI_DISABLED_REASON', 'temporarily_disabled_for_server_migration')


def _no_network(*a, **k):
    raise AssertionError('network call to Ollama while local AI is disabled')


@pytest.mark.parametrize('value,expected', [('', None), ('false', None), ('disabled_by_operator', 'disabled_by_operator'),
                                            ('temporarily_disabled_for_server_migration', 'temporarily_disabled_for_server_migration'),
                                            ('yes', 'disabled_by_operator')])
def test_reason_values(monkeypatch, value, expected):
    monkeypatch.setenv('LOCAL_AI_DISABLED_REASON', value)
    assert gw.local_ai_disabled_reason() == expected


def test_adapter_refuses(disabled):
    with pytest.raises(gw.GatewayError, match='local_ai_disabled'):
        gw.OllamaAdapter('http://127.0.0.1:11434', 'qwen3:8b', 5)


def test_identity_check_refuses_without_network(disabled):
    with mock.patch.object(mi, 'build_opener', _no_network), pytest.raises(mi.IdentityError, match='local_ai_disabled'):
        mi._get('http://127.0.0.1:11434', '/api/version', 2)


def test_probe_and_unload_make_no_request(disabled):
    s = local_ai.LocalAISettings('ollama', 'http://127.0.0.1:11434', 'qwen3:8b', None, 4096, 0.1, 512, 1, 60, 8, '5m')
    with mock.patch('urllib.request.OpenerDirector.open', _no_network):
        assert local_ai.probe(s, ttl=0) == (False, False, None)
        assert local_ai.make_room_for('qwen3:8b', 'http://127.0.0.1:11434') == []


def test_disabled_state_message(disabled):
    st = local_ai.disabled_state()
    assert st['state'] == 'temporarily_disabled_for_server_migration'
    assert 'موقتاً غیرفعال' in st['message_fa']


def test_enabled_when_unset(monkeypatch):
    monkeypatch.delenv('LOCAL_AI_DISABLED_REASON', raising=False)
    assert local_ai.disabled_state() is None
