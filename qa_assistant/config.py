import os
 
_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(_DIR, ".."))
 
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DATA_PATH = os.path.join(DATA_DIR, "Mental_Health_FAQ.csv")
DB_PATH = os.path.join(DATA_DIR, "conversations.db")