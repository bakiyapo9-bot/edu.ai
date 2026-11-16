"""Assistant EduIA en terminal : on parle (ou on tape), l'IA répond à voix haute.

Mode vocal : le micro capte la question → Google Speech la transcrit (fr-FR)
→ Groq génère la réponse → edge-tts la lit à voix haute → le micro se rouvre.
Pendant qu'Akwaba parle, appuie sur Entrée pour le couper (Windows).
(Le micro reste fermé pendant qu'il parle : sinon, sans casque, il capterait sa propre voix.)
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import tempfile
from types import ModuleType

from openai.types.chat import ChatCompletionMessageParam

from ai_client import MISSING_KEY_MESSAGE, MODEL, explain_error, make_client

msvcrt: ModuleType | None = None
if sys.platform == "win32":
    import msvcrt as _msvcrt

    msvcrt = _msvcrt
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

# Ces paquets ne sont nécessaires qu'au mode vocal : on les importe à la demande.
try:
    import edge_tts
    import pygame
    import speech_recognition as sr
except ImportError as exc:  # pragma: no cover — message d'installation
    print(f"❌ Dépendance manquante ({exc.name}). Lance : python -m pip install -r requirements.txt")
    sys.exit(1)

# ==============================
# CONFIG
# ==============================
VOIX_TTS = os.environ.get("EDUIA_VOICE", "fr-FR-DeniseNeural")
LANGUE = "fr-FR"
MAX_HISTORIQUE = 30          # messages conservés (hors prompt système)
DELAI_ECOUTE = 8             # secondes d'attente avant de considérer un silence
DUREE_MAX_PHRASE = 20        # secondes max pour une question
MOTS_QUITTER = {"quitter", "quit", "exit", "q", "au revoir", "stop", "arrête", "arrête-toi"}

client = make_client()

SYSTEM_PROMPT = """Tu es EduIA (Akwaba), un professeur virtuel bienveillant dédié aux élèves du système éducatif ivoirien.

MATIÈRES DISPONIBLES :
1. Mathématiques  2. Physique-Chimie  3. SVT  4. Philosophie  5. Français  6. Culture Générale

SALLE DE CLASSE :
- Au début, tu proposes à l'élève de choisir sa matière.
- Une fois la matière choisie, tu refuses gentiment les questions d'une autre matière :
  "Tu es en cours de Français. Dis 'changer' pour changer de matière."
- Si l'élève dit 'changer', tu proposes à nouveau le menu.

MÉTHODE : explication simple → exemple concret (contexte ivoirien) → petite question d'entraînement
→ parfois un « Le savais-tu ? » → encouragement.

RÈGLES :
- Réponds TOUJOURS en français.
- Tes réponses sont LUES À VOIX HAUTE : phrases courtes, pas de tableau, pas de markdown,
  pas d'emoji, formules écrites en mots (ex : « x au carré », « racine de 2 »).
- 4 à 6 phrases maximum, puis une question pour vérifier la compréhension."""


# ==============================
# SYNTHÈSE VOCALE
# ==============================

def texte_pour_voix(texte: str) -> str:
    """Retire le markdown et les emojis pour que la voix ne lise pas « astérisque »."""
    texte = re.sub(r"```.*?```", " ", texte, flags=re.S)
    texte = re.sub(r"[*_`#>|]+", "", texte)
    texte = re.sub(r"^\s*[-•]\s+", "", texte, flags=re.M)
    texte = re.sub(r"[\U0001F300-\U0001FAFF☀-➿️]", "", texte)
    for symbole, mot in (("√", " racine de "), ("²", " au carré"), ("³", " au cube"),
                         ("×", " fois "), ("÷", " divisé par "), ("≤", " inférieur ou égal à "),
                         ("≥", " supérieur ou égal à ")):
        texte = texte.replace(symbole, mot)
    return re.sub(r"\s+", " ", texte).strip()


async def _generer_audio(texte: str, chemin: str) -> None:
    await edge_tts.Communicate(texte, voice=VOIX_TTS).save(chemin)


def _touche_pressee() -> bool:
    """Vrai si l'élève a appuyé sur une touche (Windows), sans bloquer ni utiliser de thread."""
    if msvcrt is None or not msvcrt.kbhit():
        return False
    while msvcrt.kbhit():  # vide le tampon clavier
        msvcrt.getwch()
    return True


def parler(texte: str) -> None:
    """Lit le texte à voix haute. Une touche l'interrompt. N'échoue jamais : au pire, texte seul."""
    texte = texte_pour_voix(texte)
    if not texte:
        return
    fd, chemin = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        asyncio.run(_generer_audio(texte, chemin))
        pygame.mixer.music.load(chemin)
        pygame.mixer.music.play()
        if msvcrt is not None:
            print("   (🔊 Akwaba parle — appuie sur Entrée pour le couper)")
        interrompu = False
        horloge = pygame.time.Clock()
        while pygame.mixer.music.get_busy():
            if _touche_pressee():
                interrompu = True
                break
            horloge.tick(20)
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        if interrompu:
            print("   [Interrompu — à toi de parler]")
    except Exception as exc:  # noqa: BLE001 — réseau edge-tts ou carte son : on continue en texte
        print(f"   [Voix indisponible : {exc}]")
    finally:
        try:
            os.remove(chemin)
        except OSError:
            pass


# ==============================
# RECONNAISSANCE VOCALE
# ==============================
class Oreille:
    """Micro calibré une seule fois sur le bruit ambiant, puis réutilisé."""

    def __init__(self) -> None:
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.9          # silence qui marque la fin de phrase
        self.recognizer.dynamic_energy_threshold = True
        self.micro = sr.Microphone()
        with self.micro as source:
            print("🎚️  Calibrage du micro, reste silencieux une seconde…")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)

    def ecouter(self) -> str:
        """Retourne la phrase entendue, ou "" si rien n'a été compris."""
        with self.micro as source:
            print("🎤 Je t'écoute…")
            try:
                audio = self.recognizer.listen(source, timeout=DELAI_ECOUTE,
                                               phrase_time_limit=DUREE_MAX_PHRASE)
            except sr.WaitTimeoutError:
                return ""
        try:
            texte = self.recognizer.recognize_google(audio, language=LANGUE)
        except sr.UnknownValueError:
            print("❓ Je n'ai pas compris, répète s'il te plaît.")
            return ""
        except sr.RequestError as exc:
            print(f"🌐 Reconnaissance vocale impossible (Internet requis) : {exc}")
            return ""
        texte = str(texte).strip()
        print(f"Toi : {texte}")
        return texte


# ==============================
# IA
# ==============================
historique: list[ChatCompletionMessageParam] = []


def envoyer(question: str) -> str:
    if question.lower() == "changer":
        historique.clear()

    if client is None:
        return MISSING_KEY_MESSAGE

    historique.append({"role": "user", "content": question})
    del historique[:-MAX_HISTORIQUE]
    messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += historique
    try:
        resp = client.chat.completions.create(model=MODEL, messages=messages,
                                              max_tokens=1000, temperature=0.6)
    except Exception as exc:  # noqa: BLE001 — erreur API traduite en français
        historique.pop()  # la question n'a pas reçu de réponse
        return explain_error(exc)[0]
    reponse = (resp.choices[0].message.content or "").strip() if resp.choices else ""
    if not reponse:
        historique.pop()
        return "Je n'ai pas pu répondre, peux-tu reformuler ?"
    historique.append({"role": "assistant", "content": reponse})
    return reponse


# ==============================
# PROGRAMME PRINCIPAL
# ==============================
def choisir_mode() -> bool:
    print("\n" + "=" * 50)
    print("        EduIA — Professeur virtuel Akwaba")
    print("=" * 50)
    if client is None:
        print("\n⚠️  " + MISSING_KEY_MESSAGE)
    print("\nComment veux-tu interagir ?")
    print("  1 — Clavier (taper)")
    print("  2 — Micro (parler, Akwaba répond à voix haute)")
    while True:
        choix = input("\nTon choix [1 ou 2] : ").strip()
        if choix in ("1", "2"):
            return choix == "2"
        print("Tape 1 ou 2.")


def main() -> None:
    mode_vocal = choisir_mode()
    oreille: Oreille | None = None
    if mode_vocal:
        try:
            pygame.mixer.init()
            oreille = Oreille()
        except Exception as exc:  # noqa: BLE001 — pas de micro / carte son : repli clavier
            print(f"❌ Micro ou haut-parleurs indisponibles ({exc}). Passage en mode clavier.")
            mode_vocal = False

    print(f"\n✅ Mode {'vocal' if mode_vocal else 'clavier'} activé. "
          f"Dis ou tape « quitter » pour arrêter, « changer » pour changer de matière.\n")

    def repondre(question: str) -> None:
        reponse = envoyer(question)
        print(f"\nAkwaba : {reponse}\n")
        if mode_vocal:
            parler(reponse)

    repondre("Bonjour")
    silences = 0
    while True:
        if oreille is not None:
            question = oreille.ecouter()
            if not question:
                silences += 1
                if silences >= 3:
                    input("💤 Je n'entends rien. Appuie sur Entrée quand tu veux reparler… ")
                    silences = 0
                continue
            silences = 0
        else:
            try:
                question = input("Toi : ").strip()
            except EOFError:
                break
            if not question:
                continue

        if question.lower().strip(" .!") in MOTS_QUITTER:
            msg = "Au revoir ! Bon courage dans tes études."
            print(f"\nAkwaba : {msg}")
            if mode_vocal:
                parler(msg)
            break
        repondre(question)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAu revoir !")
