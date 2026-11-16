import os
import sys

# Permet d'importer app.py, ai_client.py et voice_bot.py depuis les tests.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
