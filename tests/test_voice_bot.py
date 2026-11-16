"""Tests du nettoyage du texte avant la synthèse vocale."""

from __future__ import annotations

import voice_bot


def test_markdown_and_emojis_are_not_read_aloud():
    out = voice_bot.texte_pour_voix("**Bravo** 👏 !\n- point *un*\n# Titre")
    assert out == "Bravo ! point un Titre"


def test_math_symbols_are_spoken_in_words():
    out = voice_bot.texte_pour_voix("√2 × 3 et x² ≤ 4")
    assert "racine de" in out and "fois" in out and "au carré" in out and "inférieur ou égal à" in out


def test_missing_key_message_without_client(monkeypatch):
    monkeypatch.setattr(voice_bot, "client", None)
    assert "GROQ_API_KEY" in voice_bot.envoyer("Bonjour")
