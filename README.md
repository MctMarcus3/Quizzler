# Python Flask Quiz Platform (Production Ready)

A dynamic, file-based quiz application built with Python and Flask. This platform supports multiple quiz types, distinct admin and student roles, and manages all data through JSON and CSV files, requiring no external database.

The student experience is a fast, responsive **Single-Page Application (SPA)** that minimizes server load, while the admin panel features a powerful, single-page editor for creating and managing complex question banks with robust validation. This version is configured for production deployment using a WSGI server and environment variables for security.

## Core Features

### Admin Features
- **Secure Admin Panel:** A separate, protected area for all quiz management at `/admin/login`.
- **Environment-Based Credentials:** Initial admin username and password are set via a secure `.env` file, not in the code.
- **In-App Quiz Creation:** Create new question banks from scratch directly within the application.
- **JSON Upload & Append:**
    - Create new quizzes by uploading a complete JSON file.
    - Append questions from a JSON file to an existing quiz bank.
- **Powerful Quiz Editor:**
    - A seamless, **one-step GUI** for setting correct answers (radio buttons for multiple-choice, checkboxes for multiple-select) that updates in real-time.
    - Dynamically add or delete questions of any type on the fly.
    - Full support for creating and editing complex **multipart questions** with nested parts.
- **Advanced Quiz Configuration:**
    - Set a timer for each quiz (a timer of `0` disables it).
    - Control whether a quiz is reviewable by students after completion.
    - **Flexible Question Selection:**
        - Serve a specific number of questions per type (e.g., 5 multiple-choice, 3 short-answer).
        - Serve a random set of questions that meets or exceeds a **target score**.
- **Robust Validation:** The server validates all questions and display rules upon saving, providing clear error messages and highlighting the problematic question to prevent broken quizzes.
- **Scalable Form Handling:** The editor is designed to handle extremely long quizzes without hitting server form field limits.

### Student Features
- **No Login Required:** Students can join a quiz instantly with just their name and a PIN.
- **Single-Page Application (SPA):** The entire quiz is loaded once, providing an instantaneous, no-reload experience for navigating between questions, which dramatically reduces server load.
- **Instructions Page:** A clear pre-quiz screen detailing the quiz name, number of questions, and time limit.
- **Incomplete Quiz Warning:** If a student tries to submit with unanswered questions, they are prompted for confirmation before the final submission.
- **Review Page:** After completion, students can review their answers, the correct answers, and their score (if enabled by the admin).
- **Prefilled Name:** The student's name is remembered for convenience when taking another quiz.

### General & Technical Features
- **Multiple Question Types:** Supports Short-Answer, Multiple-Choice (single answer), Multiple-Select (multiple answers), and Multipart questions.
- **Rich Content Support:** Questions and options fully support **LaTeX** (using `\(...\)` for inline and `$$...$$` for display) and **Markdown** tables.
- **File-Based Storage:** No database needed. Quizzes are stored as `.json` files, leaderboards as `.csv` files.
- **Production Ready:** Configured to run with a WSGI server (Gunicorn/Waitress) and uses a `.env` file for secrets.
- **Logging:** Basic production logging is configured to capture errors to a file.
- **Light/Dark Mode Toggle:** A theme switcher for user comfort.

## Technology Stack

- **Backend:**
    - **Flask:** A lightweight Python web framework.
    - **python-dotenv:** For managing environment variables.
    - **Gunicorn** (Linux/macOS) or **Waitress** (Windows): For production WSGI serving.
- **Frontend:**
    - **HTML5 / CSS3 / Vanilla JavaScript:** For structure, styling, and all dynamic SPA behavior.
    - **Pico.css:** A minimalist CSS framework.
    - **MathJax:** For rendering LaTeX.
    - **Marked.js:** For rendering Markdown.

## Project Structure

```
/quiz_site
|-- /quizzes                # Stores all quiz JSON files
|-- /leaderboards           # Stores all leaderboard CSV files
|-- /logs                   # Stores production log files
|-- /static
|   |-- /css/
|   |-- /js/
|-- /templates
|-- /views
|-- app.py                  # Main application factory
|-- config.py
|-- data_manager.py
|-- decorators.py
|-- .env                    # <-- IMPORTANT: Stores secrets (DO NOT COMMIT)
|-- .gitignore
|-- requirements.txt
|-- run.sh                  # (for Linux/macOS)
|-- run.bat                 # (for Windows)
```

## Setup and Installation

**Prerequisites:** Python 3.6+

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd quiz_site
    ```

2.  **Create a virtual environment:**
    ```bash
    # On macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # On Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install dependencies from `requirements.txt`:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create required directories:**
    In the root of the project, create the two empty directories for data storage:
    ```bash
    mkdir quizzes
    mkdir leaderboards
    ```

5.  **Create the `.env` file:**
    In the root of your project, create a file named `.env`. Copy the following content into it and **replace the placeholder values with your own secure secrets**.

    ```
    # Flask Configuration
    # Generate a long, random string for this (e.g., using a password manager or `openssl rand -hex 32`)
    FLASK_SECRET_KEY="a_very_long_and_super_random_secret_string_for_sessions"

    # Admin User Credentials for Initial Setup
    ADMIN_USERNAME="admin"
    ADMIN_PASSWORD="ChooseAReallyStrongPasswordHere"
    ```

6.  **Update your `.gitignore` file:**
    Ensure that the `.env` file is listed in your `.gitignore` to prevent accidentally committing secrets.
    ```
    .env
    ```

## Running the Application

There are two modes for running the application:

### Development Mode (for coding and testing)

This mode uses Flask's built-in server with live reloading and debugging tools.

```bash
python app.py
```
The application will be available at `http://127.0.0.1:5000`. The first time you run the app, the admin user specified in your `.env` file will be created in `users.json`.

### Production Mode (for deployment)

This mode uses a robust WSGI server, disables debug mode, and logs errors to a file. **Do not use `python app.py` for production.**

**On Linux/macOS (using Gunicorn):**
First, make the run script executable:
```bash
chmod +x run.sh
```
Then, run the script:
```bash
./run.sh
```

**On Windows (using Waitress):**
```bash
run.bat
```
The application will be served on `http://0.0.0.0:8000`. Errors will be logged to the `logs/quiz_app.log` file.

## Quiz JSON Data Format Guide

You can create or append to quizzes by uploading a JSON file. The file must have a top-level key `"questions"` containing a list of question objects.

**Example Multiple-Select Question with Inline LaTeX:**
```json
{
  "text": "Which of these are equivalent to \\(x^2\\)?",
  "type": "multiple-select",
  "options": [
    "\\(x \\cdot x\\)",
    "\\(\\frac{x^4}{x^2}\\)",
    "\\(2x\\)"
  ],
  "answer": ["\\(x \\cdot x\\)", "\\(\\frac{x^4}{x^2}\\)"],
  "score": 3
}
```

## License

This project is licensed under the MIT License.