# edu.IA — Le tuteur intelligent des lycéens ivoiriens

**edu.IA** est une plateforme éducative en français pour les élèves du lycée en Côte d'Ivoire (2nde, 1ère, Terminale — séries A, C et D). Elle réunit des **cours conformes au programme du MENA**, des **exercices**, et **Akwaba**, un tuteur basé sur l'intelligence artificielle à qui l'élève peut **écrire ou parler** : Akwaba écoute la question et **répond à voix haute**.

---

## Sommaire

1. [Le projet](#1-le-projet)
2. [Élaboration du projet](#2-élaboration-du-projet)
3. [Fonctionnalités](#3-fonctionnalités)
4. [Architecture et fonctionnement](#4-architecture-et-fonctionnement)
5. [Installation](#5-installation-sous-windows)
6. [Configuration de la clé IA](#6-configuration-de-la-clé-ia-groq)
7. [Lancement](#7-lancement)
8. [Utiliser la voix](#8-utiliser-la-voix)
9. [Tests](#9-tests)
10. [Dépannage](#10-dépannage)
11. [Structure du projet](#11-structure-du-projet)
12. [Perspectives](#12-perspectives)

---

## 1. Le projet

### Problème

Beaucoup d'élèves n'ont personne vers qui se tourner lorsqu'ils bloquent sur une notion le soir ou le week-end. Les cours particuliers coûtent cher et les ressources en ligne sont rarement adaptées au programme ivoirien ou au contexte local.

### Objectif

Offrir à chaque lycéen un **professeur disponible à toute heure, gratuit et en français**, qui :

- suit le **programme officiel** (MENA) par niveau et par série ;
- explique **simplement**, avec des **exemples du quotidien ivoirien** (FCFA, marché, attiéké, fleuve Comoé…) ;
- **guide l'élève étape par étape** sans lui donner directement la réponse, pour qu'il apprenne vraiment ;
- fonctionne **à l'écrit comme à l'oral**, sur ordinateur comme sur téléphone.

### Public visé

Élèves de 2nde (séries A, C), 1ère et Terminale (séries A, C, D).

---

## 2. Élaboration du projet

Le projet a été construit par étapes, chacune ajoutant une brique :

| Étape | Réalisation |
|------|-------------|
| **1. Conception** | Choix du public (lycée ivoirien), des matières et du parcours élève : *accueil → connexion ou invité → niveau → série → matière → cours*. Nom du tuteur : **Akwaba** (« bienvenue »). |
| **2. Maquettes des pages** | Création des premières pages séparées (`Acceuil.html`, `connexion.html`, `niveau.html`, `matiere.html`, `cours.html`), puis plusieurs itérations sur la page d'accueil. |
| **3. Application monopage** | Regroupement de tout le parcours dans `index.html` + `script.js` : navigation sans rechargement, fil d'Ariane, comptes élèves et mode invité (stockés dans le navigateur). |
| **4. Contenu pédagogique** | Saisie des leçons du programme (notions clés, définitions, exemples) et des exercices pour Mathématiques, Physique-Chimie, SVT, Histoire, Géographie et Philosophie. |
| **5. Intégration de l'IA** | Serveur **Flask** (`app.py`) qui relaie les questions vers l'API **Groq** (modèle GPT-OSS 120B, au choix dans `.env`). La clé API reste sur le serveur, jamais dans le navigateur. Prompt pédagogique : expliquer, donner un exemple, poser une question, encourager. |
| **6. Outils du chat** | Boutons « Je ne comprends pas → demander à Akwaba » sur chaque notion, « M'aider à résoudre » sur chaque exercice, génération d'exercices supplémentaires, pièces jointes, historique des conversations, panneau IA redimensionnable. |
| **7. Assistant vocal** | `voice_bot.py` : assistant en terminal qui écoute le micro (reconnaissance Google, fr-FR), interroge l'IA et répond avec une voix neuronale française (edge-tts). |
| **8. Fiabilisation** | Correction de l'envoi des messages (messages d'erreur clairs, clé manquante détectée), **conversation vocale complète dans le site** (on parle → Akwaba répond à voix haute → le micro se rouvre), suppression de l'auto-interruption du bot vocal, validation des requêtes côté serveur, tests automatisés. |

### Choix techniques

| Choix | Raison |
|------|--------|
| **Python + Flask** | Simple à installer et à comprendre, suffisant pour servir le site et relayer les appels à l'IA. |
| **Groq (format compatible OpenAI)** | Réponses très rapides, offre gratuite généreuse, modèles performants en français ; le modèle se change dans `.env` (`GROQ_MODEL`). |
| **HTML / CSS / JavaScript sans framework** | Aucune étape de compilation : le site se lance tel quel, même sur une machine modeste. |
| **Web Speech API** (navigateur) | Reconnaissance et synthèse vocales intégrées à Chrome / Edge, sans rien installer. |
| **SpeechRecognition + edge-tts + pygame** (terminal) | Voix plus naturelle pour l'assistant vocal autonome. |

---

## 3. Fonctionnalités

- 🎓 **Parcours par niveau et série** : 2nde (A, C), 1ère (A, C, D), Tle (A, C, D), avec les matières propres à chaque série.
- 📖 **Cours au programme** : notions clés, définitions et points à retenir, organisés par leçon.
- ✏️ **Exercices** + **génération d'exercices supplémentaires** par l'IA (avec un indice, sans corrigé complet).
- 🤖 **Akwaba, tuteur IA** : connaît la classe, la série et la matière de l'élève ; reste dans la matière choisie.
- 🎤 **Conversation vocale** : l'élève parle, Akwaba répond **par écrit et à voix haute**, puis réécoute.
- 📎 **Pièces jointes** (photo d'exercice, document) mentionnées à l'IA.
- 🕘 **Historique** des conversations, par élève.
- 👤 **Compte élève ou mode invité** (inscription rapide demandée pour utiliser l'IA).

---

## 4. Architecture et fonctionnement

```
 Navigateur (index.html + script.js)              Serveur Flask (app.py)            Groq
 ┌──────────────────────────────────┐   POST     ┌──────────────────────────┐  HTTPS ┌───────────┐
 │ Cours, exercices, chat Akwaba     │ ─────────► │ /api/message             │ ─────► │ GPT-OSS   │
 │ 🎤 Reconnaissance vocale (fr-FR)  │ /api/...   │  • valide la requête     │ ◄───── │   120B    │
 │ 🔊 Synthèse vocale de la réponse  │ ◄───────── │  • ajoute la clé (.env)  │        └───────────┘
 └──────────────────────────────────┘   JSON     │  • traduit les erreurs   │
                                                  │ /api/health (IA prête ?) │
                                                  └──────────────────────────┘

 Terminal : voice_bot.py ── micro → Google Speech → Groq → edge-tts → haut-parleurs
```

**Déroulement d'une question vocale dans le site :**

1. L'élève clique sur 🎤 et parle.
2. Le navigateur transcrit la phrase en texte (affiché en direct dans la zone de saisie).
3. Dès que l'élève se tait, la question est **envoyée automatiquement** à `/api/message`.
4. Le serveur ajoute le prompt pédagogique et la clé, puis interroge Groq.
5. La réponse s'affiche dans le chat **et est lue à voix haute** (le markdown et les emojis sont retirés, `x²` est lu « x au carré », `√` « racine de »…).
6. Le micro se rouvre pour la question suivante. Re-cliquer sur 🎤 ou dire « stop » arrête la conversation.

`ai_client.py` est partagé par le site et l'assistant vocal : il charge la clé depuis `.env`, crée le client Groq et transforme les erreurs de l'API en messages compréhensibles (clé invalide, pas d'Internet, trop de demandes…).

---

## 5. Installation (sous Windows)

**Prérequis :** Python 3.10, une connexion Internet, Google Chrome ou Microsoft Edge, un micro (pour la voix).

Depuis le dossier `edu.AI` :

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> Le projet utilise **un seul** environnement virtuel : `edu.AI\.venv`.
> Si PowerShell refuse d'activer l'environnement : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

---

## 6. Configuration de la clé IA (Groq)

Sans clé, Akwaba ne peut pas répondre : le chat affiche alors un message expliquant quoi faire.

1. Crée une clé gratuite sur <https://console.groq.com/keys>.
2. Copie le modèle de configuration :

   ```powershell
   Copy-Item .env.template .env
   ```

3. Ouvre `.env` et colle ta clé :

   ```dotenv
   GROQ_API_KEY=gsk_ta_cle_ici
   ```

4. **Relance** `python app.py` (la clé n'est lue qu'au démarrage).

> ⚠️ Ne partage jamais ta clé et ne commite pas le fichier `.env` (il est déjà ignoré par Git).

Options facultatives dans `.env` : `GROQ_MODEL` (autre modèle Groq), `EDUIA_VOICE` (voix edge-tts de l'assistant terminal), `PORT` (port du serveur, 5000 par défaut).

---

## 7. Lancement

### Site web

```powershell
python app.py
```

Ouvre ensuite **<http://localhost:5000>** dans Chrome ou Edge.

> ❗ N'ouvre pas `index.html` en double-cliquant dessus ni avec *Live Server* : la page doit être servie par Flask, sinon le chat et la voix ne fonctionnent pas.

### Assistant vocal en terminal

Dans un autre terminal, avec l'environnement activé :

```powershell
python voice_bot.py
```

Choisis `1` (clavier) ou `2` (micro). En mode micro : parle, Akwaba répond à voix haute, puis t'écoute à nouveau. Appuie sur **Entrée** pour le couper pendant qu'il parle. Dis « changer » pour changer de matière, « quitter » pour arrêter.

---

## 8. Utiliser la voix

| Dans le site | Action |
|-------------|--------|
| Clic sur 🎤 | Démarre la conversation vocale (autorise le micro la première fois). |
| Parler | Le texte apparaît en direct, puis part tout seul quand tu te tais. |
| Clic sur 🎤 pendant qu'Akwaba parle | Le coupe et rouvre le micro. |
| « stop », « arrête », « au revoir » ou bouton *Arrêter la voix* | Termine la conversation vocale. |
| Taper un message au clavier | Termine aussi la conversation vocale. |

En mode vocal, Akwaba répond plus brièvement (3 à 5 phrases) pour que l'écoute reste agréable.

---

## 9. Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

Les tests vérifient, sans appeler Groq : les pages servies, la détection d'une clé absente ou factice, la validation des messages, la limite de tokens, la traduction des erreurs et le nettoyage du texte lu à voix haute.

---

## 10. Dépannage

| Symptôme | Solution |
|---------|----------|
| « La clé API Groq n'est pas configurée » | Crée `.env` avec `GROQ_API_KEY=gsk_...` puis relance `python app.py`. |
| « Clé API Groq invalide » | La clé est mal copiée ou révoquée : génère-en une nouvelle sur console.groq.com. |
| « Impossible de joindre Groq » | Vérifie la connexion Internet. |
| Le message ne part pas / erreur 405 | La page est ouverte avec Live Server ou en `file://` : utilise <http://localhost:5000>. |
| Le micro ne réagit pas | Utilise Chrome ou Edge, autorise le micro (icône 🔒 de la barre d'adresse), vérifie qu'Internet fonctionne (la reconnaissance passe par le navigateur). |
| Akwaba ne parle pas | Monte le volume ; sous Windows, vérifie qu'une voix française est installée (*Paramètres → Heure et langue → Voix*). |
| Un ancien serveur répond encore | Ferme tous les terminaux où tourne `app.py` (Ctrl + C), puis relance-le depuis `.venv`. |
| `voice_bot.py` : « Micro indisponible » | Vérifie le micro par défaut dans les paramètres son de Windows. |

---

## 11. Structure du projet

```
edu.AI/
├── app.py               # Serveur Flask : site + /api/message + /api/health
├── ai_client.py         # Clé Groq, client IA, messages d'erreur (partagé)
├── voice_bot.py         # Assistant vocal / clavier en terminal
├── templates/
│   ├── index.html       # Application complète (page servie par Flask)
│   └── *.html           # Premières maquettes de pages séparées
├── statict/
│   ├── script.js        # Navigation, cours, chat, conversation vocale
│   └── Style.css        # Styles
├── tests/               # Tests automatisés (pytest)
├── .env.template        # Modèle de configuration (copier en .env)
├── requirements.txt     # Dépendances
└── requirements-dev.txt # Dépendances de test
```

---

## 12. Perspectives

- Ajouter les leçons manquantes (Français, Anglais) et compléter chaque matière.
- Analyser réellement le contenu des photos d'exercices (modèle de vision).
- Comptes élèves stockés sur le serveur (aujourd'hui dans le navigateur uniquement, mots de passe non chiffrés : à ne pas utiliser pour des données sensibles).
- Suivi de progression et quiz chronométrés pour préparer le BAC.
- Mode hors-ligne pour les cours.
