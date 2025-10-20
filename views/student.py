# views/student.py
import random
import json # <-- Make sure json is imported
from collections import defaultdict
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
from data_manager import get_all_quizzes, get_quiz_by_id, get_leaderboard, add_to_leaderboard
from decorators import quiz_session_required

student_bp = Blueprint('student', __name__)

@student_bp.route('/')
def home():
    prefill_name = request.args.get('name', '')
    return render_template('home.html', prefill_name=prefill_name)

@student_bp.route('/quiz/start', methods=['POST'])
def start_quiz():
    # This function is the same, but its redirect now leads to the SPA loader.
    pin = request.form['pin'].strip()
    name = request.form['name'].strip()
    if not name:
        flash("Please enter your name.", "warning")
        return redirect(url_for('student.home'))

    quiz = next((q for q in get_all_quizzes() if q['pin'] == pin), None)
    if quiz:
        # --- Question selection logic is the same ---
        config = quiz.get('display_config', {})
        mode = config.get('mode', 'question_count')
        final_question_indices = []
        if mode == 'total_score':
            target_score = config.get('target_score', 10)
            indexed_questions = []
            for i, q in enumerate(quiz['questions']):
                score = sum(p.get('score', 0) for p in q.get('parts', [])) if q['type'] == 'multipart' else q.get('score', 0)
                if score > 0: indexed_questions.append((i, score))
            random.shuffle(indexed_questions)
            current_score = 0
            for q_index, q_score in indexed_questions:
                if current_score >= target_score: break
                final_question_indices.append(q_index)
                current_score += q_score
        else: # 'question_count' mode
            params = config.get('parameters', {})
            questions_by_type = defaultdict(list)
            for i, q in enumerate(quiz['questions']): questions_by_type[q['type']].append(i)
            for q_type, count in params.items():
                if count > 0 and q_type in questions_by_type:
                    available = questions_by_type[q_type]
                    num_to_select = min(count, len(available))
                    final_question_indices.extend(random.sample(available, num_to_select))
        
        if not final_question_indices:
            flash("This quiz has no questions to display based on its current rules.", "danger")
            return redirect(url_for('student.home'))

        random.shuffle(final_question_indices)
        
        # --- Session setup is simpler (no 'answers' dict) ---
        session['quiz_id'] = quiz['id']
        session['start_time'] = datetime.utcnow().isoformat()
        session['name'] = name
        session['question_order'] = final_question_indices
        
        return redirect(url_for('student.instructions'))
    else:
        flash('Invalid PIN entered.')
        return redirect(url_for('student.home'))

@student_bp.route('/quiz/instructions')
@quiz_session_required
def instructions():
    quiz = get_quiz_by_id(session['quiz_id'])
    total_questions = len(session['question_order'])
    return render_template('instructions.html', quiz=quiz, total_questions=total_questions)

# --- REWRITTEN: This route now loads ALL questions for the SPA ---
@student_bp.route('/quiz')
@quiz_session_required
def take_quiz():
    quiz_id = session['quiz_id']
    quiz = get_quiz_by_id(quiz_id)
    question_order = session.get('question_order', [])
    questions_to_send = [quiz['questions'][i] for i in question_order]
    
    # Pass the full list of questions to the template
    return render_template('quiz.html', quiz=quiz, quiz_data=questions_to_send)

# --- DELETED: The old /quiz/<q_num> and /quiz/answer routes are gone ---

# --- REWRITTEN: This is now the single endpoint for submitting all answers ---
@student_bp.route('/quiz/submit', methods=['POST'])
@quiz_session_required
def submit_quiz():
    quiz_id = session['quiz_id']
    quiz = get_quiz_by_id(quiz_id)
    start_time = datetime.fromisoformat(session['start_time'])
    
    # Get all answers from a single hidden input field
    answers_json = request.form.get('answers')
    user_answers = json.loads(answers_json) if answers_json else {}

    score = 0
    time_expired = (datetime.utcnow() - start_time).total_seconds() > quiz['timer'] + 5
    
    if quiz['timer'] > 0 and time_expired:
        flash("Time ran out! Your score was not recorded.", "warning")
        score = 0
    else:
        question_order = session['question_order']
        for i, actual_idx in enumerate(question_order):
            q_num_str = str(i)
            question = quiz['questions'][actual_idx]
            user_answer = user_answers.get(q_num_str)
            
            if user_answer is not None:
                # --- Scoring logic is the same, but adapted for the new answer format ---
                if question.get('type') == 'multiple-select':
                    if set(user_answer) == set(question['answer']): score += question.get('score', 1)
                elif question.get('type') == 'multipart':
                    for part_idx, part in enumerate(question.get('parts', [])):
                        if len(user_answer) > part_idx and user_answer[part_idx] is not None:
                            user_part_answer = user_answer[part_idx]
                            if part['type'] == 'multiple-select':
                                if set(user_part_answer) == set(part['answer']): score += part.get('score', 1)
                            else:
                                if str(user_part_answer).strip().lower() == str(part['answer']).lower(): score += part.get('score', 1)
                else:
                    if str(user_answer).strip().lower() == str(question['answer']).lower(): score += question.get('score', 1)
    
    add_to_leaderboard(quiz_id, session['name'], score)
    
    # --- Review data and session cleanup logic is the same ---
    review_items = []
    question_order = session['question_order']
    for i, actual_idx in enumerate(question_order):
        question = quiz['questions'][actual_idx]
        user_answer = user_answers.get(str(i))
        review_items.append({'question': question, 'user_answer': user_answer})
    
    session['review_data'] = review_items
    session['student_name_final'] = session.get('name', '')
    session.pop('quiz_id', None)
    session.pop('start_time', None)
    session.pop('name', None)
    session.pop('question_order', None)
    
    return redirect(url_for('student.leaderboard', quiz_id=quiz_id))
# Ensure the leaderboard function is also present
@student_bp.route('/leaderboard/<quiz_id>')
def leaderboard(quiz_id):
    quiz = get_quiz_by_id(quiz_id)
    quiz_name = quiz['name'] if quiz else 'Unknown Quiz'
    leaderboard_data = get_leaderboard(quiz_id)
    # Pass reviewability and student name to the template
    is_reviewable = quiz.get('is_reviewable', False)
    student_name = session.get('student_name_final', '')
    return render_template('leaderboard.html', leaderboard=leaderboard_data, quiz_name=quiz_name, is_reviewable=is_reviewable, quiz_id=quiz_id, student_name=student_name)

# --- NEW ROUTE for the review page ---
@student_bp.route('/quiz/review/<quiz_id>')
def review_quiz(quiz_id):
    # Pop the data to ensure it can only be reviewed once
    review_items = session.pop('review_data', None)
    if not review_items:
        flash("Review data is no longer available. Please start a new quiz.", "warning")
        return redirect(url_for('student.home'))
    
    quiz = get_quiz_by_id(quiz_id)
    return render_template('review.html', review_items=review_items, quiz_name=quiz['name'])