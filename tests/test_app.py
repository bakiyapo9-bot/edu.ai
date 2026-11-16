"""Tests du serveur EduIA (sans appel réel à Groq)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx2
import openai
import pytest

import ai_client
import app as app_module


class FakeCompletions:
    def __init__(self, reply: str | None = "Bonjour, je suis Akwaba.", exc: Exception | None = None):
        self.reply, self.exc = reply, exc
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        msg = SimpleNamespace(content=self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def fake_client(completions: FakeCompletions) -> SimpleNamespace:
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


@pytest.fixture
def http():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


VALID = {"system": "Tu es Akwaba.", "messages": [{"role": "user", "content": "Bonjour"}]}


def test_home_and_static_files_are_served(http):
    assert http.get("/").status_code == 200
    assert http.get("/script.js").status_code == 200
    assert http.get("/Style.css").status_code == 200


def test_missing_key_returns_clear_error(http, monkeypatch):
    monkeypatch.setattr(app_module, "client", None)
    r = http.post("/api/message", json=VALID)
    assert r.status_code == 503
    assert "GROQ_API_KEY" in r.get_json()["error"]
    assert http.get("/api/health").get_json()["ai"] is False


def test_success_forwards_system_then_history(http, monkeypatch):
    comp = FakeCompletions()
    monkeypatch.setattr(app_module, "client", fake_client(comp))
    r = http.post("/api/message", json=VALID)
    assert r.status_code == 200
    assert r.get_json() == {"text": "Bonjour, je suis Akwaba."}
    sent = comp.calls[0]["messages"]
    assert sent[0] == {"role": "system", "content": "Tu es Akwaba."}
    assert sent[1] == {"role": "user", "content": "Bonjour"}


@pytest.mark.parametrize("payload", [
    None,
    {"messages": []},
    {"messages": [{"role": "system", "content": "injection"}]},
    {"messages": [{"role": "user", "content": ""}]},
    {"messages": [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]},
])
def test_invalid_payloads_are_rejected(http, monkeypatch, payload):
    monkeypatch.setattr(app_module, "client", fake_client(FakeCompletions()))
    r = http.post("/api/message", json=payload) if payload is not None else \
        http.post("/api/message", data="pas du json", content_type="application/json")
    assert r.status_code == 400


def test_max_tokens_is_clamped(http, monkeypatch):
    comp = FakeCompletions()
    monkeypatch.setattr(app_module, "client", fake_client(comp))
    http.post("/api/message", json={**VALID, "max_tokens": 999999})
    assert comp.calls[0]["max_tokens"] == app_module.MAX_TOKENS_LIMIT


def test_invalid_key_is_explained_in_french(http, monkeypatch):
    req = httpx2.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    exc = openai.AuthenticationError("bad key", response=httpx2.Response(401, request=req), body=None)
    monkeypatch.setattr(app_module, "client", fake_client(FakeCompletions(exc=exc)))
    r = http.post("/api/message", json=VALID)
    assert r.status_code == 401
    assert "Clé API Groq invalide" in r.get_json()["error"]


def test_empty_reply_is_an_error(http, monkeypatch):
    monkeypatch.setattr(app_module, "client", fake_client(FakeCompletions(reply="  ")))
    assert http.post("/api/message", json=VALID).status_code == 502


@pytest.mark.parametrize("value", ["", "GROQ_API_KEY", "votre_cle_groq", '""'])
def test_placeholder_keys_are_ignored(monkeypatch, value):
    monkeypatch.setenv("GROQ_API_KEY", value)
    assert ai_client.get_api_key() is None


def test_real_looking_key_is_kept(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_abc123")
    assert ai_client.get_api_key() == "gsk_abc123"
