"""Serveur web EduIA : sert le site et relaie les questions vers le tuteur IA Akwaba (Groq)."""

from __future__ import annotations

import os
import sys
from typing import Any

from flask import Flask, Response, jsonify, request
from openai.types.chat import ChatCompletionMessageParam

from ai_client import MISSING_KEY_MESSAGE, MODEL, ROOT, explain_error, make_client

# Console Windows en UTF-8 pour éviter les UnicodeEncodeError sur les emojis.
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

app = Flask(__name__, static_folder="statict", static_url_path="")
client = make_client()

# Limites de sécurité sur ce que le navigateur peut envoyer.
MAX_MESSAGES = 40
MAX_CONTENT_CHARS = 8000
MAX_SYSTEM_CHARS = 6000
MAX_TOKENS_LIMIT = 2000
ALLOWED_ROLES = {"user", "assistant"}


@app.route("/")
def home() -> Response:
    with open(os.path.join(ROOT, "templates", "index.html"), "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")


@app.route("/api/health")
def health() -> Response:
    """Permet au site de savoir si l'IA est prête (clé configurée)."""
    return jsonify({"ai": client is not None, "model": MODEL})


def _clean_messages(raw: Any) -> list[dict[str, str]] | None:
    """Valide l'historique envoyé par le navigateur. Retourne None s'il est invalide."""
    if not isinstance(raw, list) or not raw:
        return None
    cleaned: list[dict[str, str]] = []
    for m in raw[-MAX_MESSAGES:]:
        if not isinstance(m, dict):
            return None
        role, content = m.get("role"), m.get("content")
        if role not in ALLOWED_ROLES or not isinstance(content, str) or not content.strip():
            return None
        cleaned.append({"role": role, "content": content[:MAX_CONTENT_CHARS]})
    if cleaned[-1]["role"] != "user":
        return None
    return cleaned


@app.route("/api/message", methods=["POST"])
def message() -> tuple[Response, int] | Response:
    """Relais sécurisé vers l'API Groq : la clé ne quitte jamais le serveur."""
    if client is None:
        return jsonify({"error": MISSING_KEY_MESSAGE}), 503

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Requête invalide : JSON attendu."}), 400

    history = _clean_messages(data.get("messages"))
    if history is None:
        return jsonify({"error": "Requête invalide : historique de messages incorrect."}), 400

    messages: list[ChatCompletionMessageParam] = []
    system = data.get("system")
    if isinstance(system, str) and system.strip():
        messages.append({"role": "system", "content": system[:MAX_SYSTEM_CHARS]})
    for m in history:
        if m["role"] == "user":
            messages.append({"role": "user", "content": m["content"]})
        else:
            messages.append({"role": "assistant", "content": m["content"]})

    try:
        max_tokens = max(1, min(int(data.get("max_tokens", 1000)), MAX_TOKENS_LIMIT))
    except (TypeError, ValueError):
        max_tokens = 1000

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.6,
        )
    except Exception as exc:  # noqa: BLE001 — traduit toute erreur API en message lisible
        text, status = explain_error(exc)
        app.logger.warning("Erreur Groq (%s) : %s", status, exc)
        return jsonify({"error": text}), status

    reply = (resp.choices[0].message.content or "").strip() if resp.choices else ""
    if not reply:
        return jsonify({"error": "Akwaba n'a pas renvoyé de réponse. Réessaie."}), 502
    return jsonify({"text": reply})


if __name__ == "__main__":
    if client is None:
        print("⚠️  " + MISSING_KEY_MESSAGE)
    else:
        print(f"✅ Tuteur IA prêt (modèle : {MODEL})")
    port = int(os.environ.get("PORT", "5000"))
    print(f"➡  EduIA → http://localhost:{port}")
    # 127.0.0.1 : le débogueur Flask n'est jamais exposé au réseau local.
    app.run(host="127.0.0.1", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
