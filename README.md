# Python Flask Quiz Platform

A dynamic, file-based quiz application built with Python and Flask. This platform supports multiple quiz types, distinct admin and student roles, and manages all data through JSON and CSV files, requiring no external database.

The student experience is a fast, responsive **Single-Page Application (SPA)** that minimizes server load, while the admin panel features a powerful, single-page editor for creating and managing complex question banks with robust validation.

## Core Features

### Admin Features
- **Secure Admin Panel:** A separate, protected area for all quiz management at `/admin/login`.
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
- **Robust Validation:** The server validates all questions (for logical consistency) and display rules (for feasibility) upon saving, providing clear error messages and highlighting the problematic question to prevent broken quizzes.
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
- **Rich Content Support:** Questions and options fully support **LaTeX** for mathematical notation (via MathJax) and **Markdown** for tables (via Marked.js).
- **File-Based Storage:** No database needed. Quizzes are stored as individual `.json` files and leaderboards as `.csv` files.
- **Leaderboards:** A unique leaderboard is generated for each quiz.
- **Light/Dark Mode Toggle:** A theme switcher for user comfort.

## Technology Stack

- **Backend:**
    - **Flask:** A lightweight Python web framework.
    - **Werkzeug:** For secure password hashing.
- **Frontend:**
    - **HTML5 / CSS3 / Vanilla JavaScript:** For structure, styling, and all dynamic SPA behavior.
    - **Pico.css:** A minimalist CSS framework for a clean, modern look.
    - **MathJax:** For rendering LaTeX mathematical formulas.
    - **Marked.js:** For rendering Markdown tables.

## Project Structure

```
/quiz_site
|-- /quizzes                # Stores all quiz JSON files
|-- /leaderboards           # Stores all leaderboard CSV files
|-- /static
|   |-- /css/
|   |-- /js/
|-- /templates
|   |-- admin_dashboard.html
|   |-- create_quiz.html
|   |-- edit_quiz.html
|   |-- home.html
|   |-- instructions.html
|   |-- layout.html
|   |-- leaderboard.html
|   |-- quiz.html
|   |-- review.html
|-- /views
|   |-- __init__.py
|   |-- admin.py
|   |-- auth.py
|   |-- student.py
|-- app.py                  # Main application factory
|-- config.py
|-- data_manager.py
|-- decorators.py
|-- users.json              # Stores admin credentials
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

3.  **Install dependencies:**
    Create a `requirements.txt` file with the following content:
    ```
    Flask
    Werkzeug
    ```
    Then run:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create required directories:**
    In the root of the project, create the two empty directories for data storage:
    ```bash
    mkdir quizzes
    mkdir leaderboards
    ```

5.  **Run the application:**
    ```bash
    python app.py
    ```
    The application will be available at `http://127.0.0.1:5000`.

## Usage Guide

### Administrator Workflow

1.  **Login:** Navigate to `http://127.0.0.1:5000/admin/login`.
    - **Default credentials:** `username: admin`, `password: admin`.
    - On the first successful login, a `users.json` file will be created to store the hashed password.

2.  **Create a Quiz:**
    - On the dashboard, click "Create Quiz".
    - Give the quiz a name, set a timer (in seconds), and decide if it should be reviewable.
    - You will be redirected to the **Quiz Editor**.

3.  **Edit a Quiz:**
    - Use the "Add New Question" controls to add questions of any type.
    - For Multiple-Choice and Multiple-Select questions, type the options into the `textarea` (one per line), and a GUI will appear instantly, allowing you to select the correct answer(s).
    - Configure the **Question Selection Mode** (either by count or by target score).
    - Click "Save Changes". The server will validate the entire quiz before saving.

4.  **Get the PIN:** The unique PIN for each quiz is displayed on the admin dashboard. Share this PIN with students.

### Student Workflow

1.  **Join a Quiz:** Go to the homepage (`http://127.0.0.1:5000`).
2.  Enter your name and the PIN provided by the administrator.
3.  **Review Instructions:** You will see a summary of the quiz. Click "Begin Quiz" to start.
4.  **Answer Questions:** Answer each question one at a time. Navigation is instantaneous.
5.  **Submit:** When you click "Finish Quiz," you will be warned if you have any unanswered questions.
6.  **View Leaderboard:** After finishing, you will see the leaderboard for that quiz.
7.  **Review Answers:** If the admin enabled it, a "Review Your Answers" button will be available on the leaderboard page.

## Quiz JSON Data Format Guide

You can create or append to quizzes by uploading a JSON file. The file must have a top-level key `"questions"` containing a list of question objects.

### Example Question Types

**Short-Answer:**
```json
{
  "text": "What is the chemical symbol for gold?",
  "type": "short-answer",
  "answer": "Au",
  "score": 2
}
```

**Multiple-Choice (Single Answer):**
```json
{
  "text": "What is the largest planet in our solar system?",
  "type": "multiple-choice",
  "options": ["Earth", "Jupiter", "Mars", "Saturn"],
  "answer": "Jupiter",
  "score": 1
}
```

**Multiple-Select (Multiple Answers):**
The `answer` must be a list of strings.
```json
{
  "text": "Which of the following are programming languages?",
  "type": "multiple-select",
  "options": ["Python", "HTML", "Java", "CSS"],
  "answer": ["Python", "Java"],
  "score": 3
}
```

**Multipart Question:**
Contains a list of `parts`, where each part is a complete question object.
```json
{
  "text": "This question is about geography. For inline math, use \\( ... \\).",
  "type": "multipart",
  "parts": [
    {
      "text": "Part A: What is the longest river in the world?",
      "type": "short-answer",
      "answer": "The Nile",
      "score": 2
    },
    {
      "text": "Part B: Which of these continents are in the Southern Hemisphere?",
      "type": "multiple-select",
      "options": ["North America", "Australia", "Antarctica", "Europe"],
      "answer": ["Australia", "Antarctica"],
      "score": 3
    }
  ]
}
```

## License

This project is licensed under the MIT License.