import json
import random
import uuid
import os
from collections import defaultdict
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
from data_manager import get_all_quizzes, get_quiz_by_id, get_leaderboard, add_to_leaderboard, load_temp_session_data, save_temp_session_data
from decorators import quiz_session_required

student_bp = Blueprint('student', __name__)
TEMP_REVIEW_DIR = 'temp_reviews'

@student_bp.route('/')
def home():
    prefill_name = request.args.get('name', '')
    return render_template('home.html', prefill_name=prefill_name)

@student_bp.route('/quiz/start', methods=['POST'])
def start_quiz():
    pin = request.form['pin'].strip()
    name = request.form['name'].strip()
    if not name:
        flash("Please enter your name.", "warning")
        return redirect(url_for('student.home'))

    quiz = next((q for q in get_all_quizzes() if q['pin'] == pin), None)
    if quiz:
        config = quiz.get('display_config', {})
        mode = config.get('mode', 'question_count')
        
        final_question_indices = []
        # (This is the correct, complex question selection logic)
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

@student_bp.route('/quiz')
@quiz_session_required
def take_quiz():
    quiz_id = session['quiz_id']
    quiz = get_quiz_by_id(quiz_id)
    question_order = session.get('question_order', [])
    questions_to_send = [quiz['questions'][i] for i in question_order]
    return render_template('quiz.html', quiz=quiz, quiz_data=questions_to_send)

@student_bp.route('/quiz/submit', methods=['POST'])
@quiz_session_required
def submit_quiz():
    quiz_id = session.get('quiz_id')
    name = session.get('name')
    start_time_str = session.get('start_time')
    question_order = session.get('question_order', [])

    if not all([quiz_id, name, start_time_str]):
        flash("Your session expired. Please start the quiz again.", "warning")
        return redirect(url_for('student.home'))
        
    quiz = get_quiz_by_id(quiz_id)
    start_time = datetime.fromisoformat(start_time_str)
    
    answers_json = request.form.get('answers')
    user_answers = json.loads(answers_json) if answers_json else {}

    score = 0

    if not question_order:
        flash("The quiz had no questions to score.", "warning")
    else:
        time_expired = (quiz.get('timer', 0) > 0) and ((datetime.utcnow() - start_time).total_seconds() > quiz['timer'] + 5)
        
        if not time_expired:
            for i, actual_idx in enumerate(question_order):
                question = quiz['questions'][actual_idx]
                user_answer = user_answers.get(str(i))
                if user_answer is not None:
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

    # This block now correctly builds the review data
    review_items = []
    if question_order:
        for i, actual_idx in enumerate(question_order):
            question = quiz['questions'][actual_idx]
            user_answer = user_answers.get(str(i))
            review_items.append({'question': question, 'user_answer': user_answer})

    # Save to leaderboard (this is correct)
    add_to_leaderboard(quiz_id, name, score)
    
    # Exclusively use the correct review_session_id system
    if review_items and quiz.get('is_reviewable'):
        review_session_id = str(uuid.uuid4())
        save_temp_session_data(review_session_id, review_items)
        session['review_session_id'] = review_session_id

    # DELETED: All logic related to 'review_token' has been removed.

    session['student_name_final'] = name
    session.pop('quiz_id', None)
    session.pop('start_time', None)
    session.pop('name', None)
    session.pop('question_order', None)
    
    return redirect(url_for('student.leaderboard', quiz_id=quiz_id))


@student_bp.route('/leaderboard/<quiz_id>')
def leaderboard(quiz_id):
    quiz = get_quiz_by_id(quiz_id)
    quiz_name = quiz['name'] if quiz else 'Unknown Quiz'
    leaderboard_data = get_leaderboard(quiz_id)
    is_reviewable = quiz.get('is_reviewable', False) if quiz else False
    student_name = session.get('student_name_final', '')
    
    review_session_id = session.get('review_session_id')
    
    return render_template(
        'leaderboard.html', 
        leaderboard=leaderboard_data, 
        quiz_name=quiz_name, 
        is_reviewable=is_reviewable, 
        quiz_id=quiz_id,  # This is crucial: Pass the quiz_id to the template
        student_name=student_name,
        review_session_id=review_session_id # Pass the correct session ID
    )

@student_bp.route('/quiz/review/<quiz_id>')
def review_quiz(quiz_id):
    """
    Displays the student's answers and the correct answers for a completed quiz.
    This is the final step in the student workflow.
    """
    # 1. Get the unique ID for this review session from the user's cookie.
    # We pop it to ensure it can only be used once.
    review_session_id = session.pop('review_session_id', None)

    if not review_session_id:
        flash("Review data has expired or is no longer available. Please start a new quiz.", "warning")
        return redirect(url_for('student.home'))
        
    # 2. Load the large review data from the corresponding temporary file on the server.
    # The load_temp_session_data function also deletes the file after reading.
    review_items = load_temp_session_data(review_session_id)
    
    # 3. Handle the case where the temporary file might have been deleted or expired.
    if not review_items:
        flash("Review data could not be found. It may have expired.", "warning")
        return redirect(url_for('student.home'))
    
    # 4. Get the quiz's name for display purposes.
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        # Failsafe in case the quiz was deleted between submission and review.
        flash("The quiz you are trying to review could not be found.", "danger")
        return redirect(url_for('student.home'))

    # 5. Render the review page with the loaded data.
    return render_template('review.html', review_items=review_items, quiz_name=quiz['name'])