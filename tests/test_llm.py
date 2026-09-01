import sys
import types

import pytest

from sleeper_recap import llm


def test_unknown_provider_exits():
    with pytest.raises(SystemExit, match="unknown provider"):
        llm.generate("grok", "x", "hi")


def test_openai_missing_key_exits(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        llm.generate("openai", "gpt-5", "hi")


def test_gemini_missing_key_exits(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
        llm.generate("gemini", "gemini-2.5-pro", "hi")


def test_missing_sdk_message(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(SystemExit, match="pip install openai"):
        llm.generate("openai", "gpt-5", "hi")


def test_anthropic_call_path(monkeypatch):
    fake = types.SimpleNamespace()

    class FakeBlock:
        type = "text"
        text = "Subject: Week 1\n\nHello league"

    class FakeResponse:
        stop_reason = "end_turn"
        content = [FakeBlock()]

    class FakeMessages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-opus-5"
            assert kwargs["messages"][0]["content"] == "hi"
            return FakeResponse()

    class FakeAnthropic:
        def __init__(self):
            self.messages = FakeMessages()

    fake.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    assert llm.generate("anthropic", "claude-opus-5", "hi") == "Subject: Week 1\n\nHello league"
