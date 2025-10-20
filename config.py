# config.py

import os
from dotenv import load_dotenv

# Load variables from .env file into the environment
load_dotenv()

# --- Application Configuration ---
# Get the secret key from the environment, with a fallback for safety
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'a-fallback-secret-key-for-dev')

# --- Data Storage Paths (Unchanged) ---
USER_DATA_FILE = 'users.json'
QUIZ_DIR = 'quizzes'
LEADERBOARD_DIR = 'leaderboards'

# --- Initial Admin User Configuration ---
# Get admin credentials from the environment
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin')