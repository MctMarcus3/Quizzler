import json
import os
import csv
from datetime import datetime
from werkzeug.security import generate_password_hash
from config import USER_DATA_FILE, QUIZ_DIR, LEADERBOARD_DIR
from config import USER_DATA_FILE, ADMIN_USERNAME, ADMIN_PASSWORD
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash

def load_users():
    """
    Loads user data from users.json. If the file doesn't exist,
    it creates it with the initial admin user from the .env configuration.
    """
    if not os.path.exists(USER_DATA_FILE):
        print(f"User data file not found. Creating '{USER_DATA_FILE}' with initial admin user.")
        # Create the default admin user from the config
        initial_users = {
            ADMIN_USERNAME: {
                'password': generate_password_hash(ADMIN_PASSWORD),
                'role': 'admin'
            }
        }
        save_users(initial_users)
        return initial_users

    with open(USER_DATA_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    """Saves user data to the users.json file."""
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# --- Helper function for backward compatibility ---
def _ensure_backward_compatibility(quiz_data):
    """
    Checks for and adds missing keys for all new features to older quiz files.
    This function is now upgraded to handle all recent feature additions.
    """
    # Check for the original display_config
    if 'display_config' not in quiz_data:
        print(f"INFO: Upgrading old quiz format for quiz ID {quiz_data.get('id')}. Adding default 'display_config'.")
        quiz_data['display_config'] = {
            'mode': 'question_count',
            'parameters': { 'multiple-choice': 0, 'short-answer': 0, 'multiple-select': 0, 'multipart': 0 },
            'target_score': 10
        }

    # --- UPGRADE: Add default (disabled) practice mode configuration ---
    if 'practice_mode_config' not in quiz_data:
        print(f"INFO: Upgrading quiz ID {quiz_data.get('id')}. Adding default 'practice_mode_config'.")
        quiz_data['practice_mode_config'] = {
            'enabled': False,
            'allow_student_selection': False,
            'max_questions_limit': 10
        }

    # --- UPGRADE: Generate a practice PIN if one doesn't exist ---
    if 'practice_pin' not in quiz_data:
        print(f"INFO: Upgrading quiz ID {quiz_data.get('id')}. Generating new 'practice_pin'.")
        # Generate a new random 6-digit pin for practice mode
        quiz_data['practice_pin'] = str(uuid.uuid4().int)[-6:]

    # --- UPGRADE: Add other missing fields with safe defaults ---
    if 'is_reviewable' not in quiz_data:
        quiz_data['is_reviewable'] = False
    
    if 'instructions' not in quiz_data:
        quiz_data['instructions'] = ''

    return quiz_data


def get_all_quizzes():
    """Scans the quiz directory and returns data from all quiz JSON files."""
    quizzes = []
    if not os.path.exists(QUIZ_DIR):
        os.makedirs(QUIZ_DIR)
    for filename in os.listdir(QUIZ_DIR):
        if filename.endswith('.json'):
            with open(os.path.join(QUIZ_DIR, filename), 'r') as f:
                try:
                    quiz_data = json.load(f)
                    # --- START OF THE FIX ---
                    quiz_data = _ensure_backward_compatibility(quiz_data)
                    # --- END OF THE FIX ---
                    quizzes.append(quiz_data)
                except json.JSONDecodeError:
                    print(f"ERROR: Could not parse {filename}. It may be a corrupted JSON file.")
    return quizzes

def get_quiz_by_id(quiz_id):
    """Loads a single quiz by its ID and ensures it's backward-compatible."""
    quiz_path = os.path.join(QUIZ_DIR, f"{quiz_id}.json")
    if os.path.exists(quiz_path):
        with open(quiz_path, 'r') as f:
            try:
                quiz_data = json.load(f)
                # --- START OF THE FIX ---
                quiz_data = _ensure_backward_compatibility(quiz_data)
                # --- END OF THE FIX ---
                return quiz_data
            except json.JSONDecodeError:
                print(f"ERROR: Could not parse {quiz_id}.json. It may be a corrupted JSON file.")
                return None
    return None

def save_quiz(quiz_id, quiz_data):
    """Saves a quiz to a JSON file named after its ID."""
    if not os.path.exists(QUIZ_DIR):
        os.makedirs(QUIZ_DIR)
    with open(os.path.join(QUIZ_DIR, f"{quiz_id}.json"), 'w') as f:
        json.dump(quiz_data, f, indent=4)

# --- Leaderboard Management (CSV) ---

def get_leaderboard(quiz_id):
    """Reads a leaderboard CSV file and returns its data, sorted by score."""
    leaderboard = []
    leaderboard_path = os.path.join(LEADERBOARD_DIR, f"{quiz_id}.csv")
    if os.path.exists(leaderboard_path):
        with open(leaderboard_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Ensure score is an integer for correct sorting
                row['score'] = int(row['score'])
                leaderboard.append(row)
    # Sort by score (descending)
    leaderboard.sort(key=lambda x: x['score'], reverse=True)
    return leaderboard

def add_to_leaderboard(quiz_id, username, score):
    """Appends a new entry to a leaderboard CSV file."""
    if not os.path.exists(LEADERBOARD_DIR):
        os.makedirs(LEADERBOARD_DIR)
        
    leaderboard_path = os.path.join(LEADERBOARD_DIR, f"{quiz_id}.csv")
    file_exists = os.path.exists(leaderboard_path)
    
    with open(leaderboard_path, 'a', newline='') as f:
        fieldnames = ['username', 'score', 'timestamp']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()  # Write header if file is new
            
        writer.writerow({
            'username': username,
            'score': score,
            'timestamp': datetime.utcnow().isoformat()
        })

TEMP_SESSION_DIR = 'temp_sessions'

def save_temp_session_data(session_id, data):
    """Saves temporary data (like review data) to a server-side file."""
    if not os.path.exists(TEMP_SESSION_DIR):
        os.makedirs(TEMP_SESSION_DIR)
    
    file_path = os.path.join(TEMP_SESSION_DIR, f"{session_id}.json")
    with open(file_path, 'w') as f:
        json.dump(data, f)

def load_temp_session_data(session_id):
    """Loads and then deletes temporary session data from a file."""
    file_path = os.path.join(TEMP_SESSION_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Clean up the file after it's been read once to prevent reuse
        os.remove(file_path)
        return data
    return None

def delete_quiz(quiz_id):
    """Deletes a quiz JSON file and its associated leaderboard file."""
    quiz_deleted = False
    leaderboard_deleted = False

    # 1. Delete the quiz file
    quiz_file_path = os.path.join(QUIZ_DIR, f"{quiz_id}.json")
    try:
        if os.path.exists(quiz_file_path):
            os.remove(quiz_file_path)
            quiz_deleted = True
    except OSError as e:
        print(f"Error deleting quiz file {quiz_id}: {e}")

    # 2. Delete the associated leaderboard file
    # --- FIX: The filename must match the one used by get_leaderboard and add_to_leaderboard ---
    leaderboard_file_path = os.path.join(LEADERBOARD_DIR, f"{quiz_id}.csv")
    try:
        if os.path.exists(leaderboard_file_path):
            os.remove(leaderboard_file_path)
    except OSError as e:
        print(f"Error deleting leaderboard file for quiz {quiz_id}: {e}")

    # Return True only if the main quiz file was successfully deleted
    return quiz_deleted