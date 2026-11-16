"""Accès partagé à l'API Groq (format compatible OpenAI) pour EduIA.

Utilisé par le serveur web (app.py) et par l'assistant vocal (voice_bot.py) :
- chargement de la clé depuis le fichier .env situé à côté de ce fichier ;
- détection des clés absentes ou laissées à leur valeur d'exemple ;
- traduction des erreurs de l'API en messages clairs, en français.
"""

from __future__ import annotations

import os
from typing import Final

import openai
from dotenv import load_dotenv
from openai import OpenAI

ROOT: Final = os.path.dirname(os.path.abspath(__file__))

# Charge toujours le .env du projet, même si le script est lancé depuis un autre dossier.
load_dotenv(os.path.join(ROOT, ".env"))

BASE_URL: Final = "https://api.groq.com/openai/v1"
# llama-3.3-70b-versatile a été retiré par Groq : liste à jour sur https://console.groq.com/docs/models
MODEL: Final = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

# Valeurs d'exemple qui ne sont pas de vraies clés.
_PLACEHOLDERS: Final = {"", "GROQ_API_KEY", "votre_cle_groq", "gsk_...", "changeme"}


def get_api_key() -> str | None:
    """Retourne la clé Groq configurée, ou None si elle est absente ou factice."""
    key = os.environ.get("GROQ_API_KEY", "").strip().strip('"').strip("'")
    return None if key in _PLACEHOLDERS else key


def make_client() -> OpenAI | None:
    """Crée le client Groq, ou None si aucune clé valide n'est configurée."""
    key = get_api_key()
    if not key:
        return None
    return OpenAI(api_key=key, base_url=BASE_URL, timeout=60.0, max_retries=1)


MISSING_KEY_MESSAGE: Final = (
    "La clé API Groq n'est pas configurée. Crée le fichier .env dans le dossier edu.AI "
    "avec la ligne GROQ_API_KEY=gsk_... (clé gratuite sur https://console.groq.com/keys), "
    "puis relance le serveur."
)


def explain_error(exc: Exception) -> tuple[str, int]:
    """Convertit une exception de l'API en (message en français, code HTTP)."""
    if isinstance(exc, openai.AuthenticationError):
        return ("Clé API Groq invalide ou révoquée. Vérifie GROQ_API_KEY dans le fichier .env "
                "puis relance le serveur.", 401)
    if isinstance(exc, openai.PermissionDeniedError):
        return ("Accès refusé par Groq pour cette clé (compte ou région non autorisés).", 403)
    if isinstance(exc, openai.RateLimitError):
        return ("Trop de demandes envoyées à Groq. Patiente quelques secondes puis réessaie.", 429)
    if isinstance(exc, openai.NotFoundError):
        return (f"Le modèle « {MODEL} » est introuvable chez Groq. Change GROQ_MODEL dans .env.", 502)
    if isinstance(exc, openai.APITimeoutError):
        return ("Groq met trop de temps à répondre. Réessaie dans un instant.", 504)
    if isinstance(exc, openai.APIConnectionError):
        return ("Impossible de joindre Groq. Vérifie ta connexion Internet.", 503)
    if isinstance(exc, openai.BadRequestError):
        return (f"Requête refusée par Groq : {exc}", 400)
    if isinstance(exc, openai.APIStatusError):
        return (f"Erreur du service Groq ({exc.status_code}). Réessaie plus tard.", 502)
    return (f"Erreur inattendue : {exc}", 500)
