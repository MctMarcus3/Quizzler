# views/admin.py
from collections import defaultdict
import json
import traceback
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash
from data_manager import get_all_quizzes, get_quiz_by_id, save_quiz
from decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    quizzes = get_all_quizzes()
    return render_template('admin_dashboard.html', quizzes=quizzes)

@admin_bp.route('/upload', methods=['POST'])
@admin_required
def upload_quiz():
    file = request.files.get('file')
    if not file or not file.filename.endswith('.json'):
        flash("Please upload a valid JSON file.", "warning")
        return redirect(url_for('admin.admin_dashboard'))
        
    try:
        quiz_content = json.load(file)
        quiz_id = str(uuid.uuid4())
        
        # Prepare the full quiz data object
        new_quiz_data = {
            'id': quiz_id,
            'pin': str(uuid.uuid4().int)[:6],
            'name': quiz_content['name'],
            'timer': quiz_content.get('timer', 600),
            'questions': quiz_content['questions']
        }
        
        save_quiz(quiz_id, new_quiz_data) # <-- CHANGED
        flash(f"Quiz '{new_quiz_data['name']}' uploaded successfully!", "success")

    except (json.JSONDecodeError, KeyError) as e:
        flash(f"Error processing file: The JSON is malformed or missing required keys (e.g., 'name', 'questions').", "danger")
            
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create_quiz():
    if request.method == 'POST':
        quiz_name = request.form.get('quiz_name')
        quiz_timer = request.form.get('quiz_timer', 300, type=int)

        if not quiz_name:
            flash("Quiz name is required.", "warning")
            return render_template('create_quiz.html')

        # Create a basic quiz structure
        quiz_id = str(uuid.uuid4())
        new_quiz = {
            'id': str(uuid.uuid4()),
            'pin': str(uuid.uuid4().int)[:6],
            'name': request.form.get('quiz_name'),
            'timer': request.form.get('quiz_timer', 300, type=int),
            'is_reviewable': request.form.get('is_reviewable') == 'on',
            'display_config': {
                'mode': 'question_count',
                'parameters': { 'multiple-choice': 0, 'short-answer': 0, 'multiple-select': 0, 'multipart': 0 },
                'target_score': 10
            },
            'questions': []
        }
        
        save_quiz(quiz_id, new_quiz)
        flash(f"Quiz '{quiz_name}' created. You can now add questions.", "success")
        return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

    return render_template('create_quiz.html')


@admin_bp.route('/append/<quiz_id>', methods=['POST'])
@admin_required
def append_questions(quiz_id):
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        flash("Quiz not found.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    file = request.files.get('file')
    if not file or not file.filename.endswith('.json'):
        flash("Please upload a valid JSON file.", "warning")
        return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))
    
    try:
        data = json.load(file)
        new_questions = data.get('questions')

        if not isinstance(new_questions, list):
            flash("JSON file must contain a 'questions' key with a list of questions.", "danger")
            return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

        quiz['questions'].extend(new_questions)
        save_quiz(quiz_id, quiz)
        flash(f"{len(new_questions)} question(s) appended successfully.", "success")

    except json.JSONDecodeError:
        flash("Invalid JSON format in the uploaded file.", "danger")
    except Exception as e:
        flash(f"An error occurred while appending: {e}", "danger")

    return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))


def validate_question(q_data, q_num):
    """
    Validates a single question dictionary to ensure it's logically sound.
    Returns an error string if invalid, otherwise None.
    """
    q_type = q_data.get('type')
    if not q_data.get('text', '').strip():
        return f"Question #{q_num} is missing its main text."
    
    # Validation for types that have predefined options
    if q_type in ['multiple-choice', 'multiple-select']:
        options = q_data.get('options', [])
        if not options:
            return f"Question #{q_num} ('{q_type}') has no options defined."
        
        answers = q_data.get('answer')
        
        # It's NOT an error if 'answers' is missing on the first save of a new question.
        # However, if answers ARE provided, they must be valid.
        if answers:
            if not isinstance(answers, list):
                answers = [answers]
            
            for ans in answers:
                if ans not in options:
                    return f"Question #{q_num}: The answer '{ans}' is not listed in the provided options."
    
    # Recursive validation for multipart questions
    elif q_type == 'multipart':
        parts = q_data.get('parts', [])
        if not parts:
            return f"Question #{q_num} ('multipart') has no sub-questions (parts) defined."
        for i, part in enumerate(parts):
            part_error = validate_question(part, f"{q_num}.{i+1}")
            if part_error:
                return part_error
    
    # Validation for types that ALWAYS require an answer
    elif not q_data.get('answer'):
         return f"Question #{q_num} ('{q_type}') is missing an answer."

    return None


@admin_bp.route('/edit/<quiz_id>', methods=['GET', 'POST'])
@admin_required
def edit_quiz(quiz_id):
    """
    Handles both displaying and processing the main quiz editor page.
    This version correctly receives all data as a single JSON object.
    """
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        flash("Quiz not found.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        try:
            # 1. Get the entire quiz data from the single 'quizData' form field.
            raw_data = request.form.get('quizData')
            if not raw_data:
                raise ValueError("No quizData submitted by the form. This is a critical client-side error.")
            
            # 2. Parse this JSON string into a Python dictionary.
            form_data = json.loads(raw_data)
            
            # 3. Reconstruct the updated_quiz dictionary directly from this parsed data.
            updated_quiz = {
                'id': quiz_id,
                'pin': quiz['pin'],
                'name': form_data['name'],
                'timer': int(form_data['timer']),
                'is_reviewable': form_data.get('is_reviewable', False),
                'display_config': form_data['display_config'],
                'questions': form_data['questions']
            }

            # 4. VALIDATE the fully constructed quiz data before saving.
            # 4a. Per-Question Validation
            for i, q_data in enumerate(updated_quiz['questions']):
                error = validate_question(q_data, i + 1)
                if error:
                    flash(f"Validation Error: {error}", "danger")
                    return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id, error_q=i))

            # 4b. Display Configuration Validation
            available_counts = defaultdict(int)
            total_possible_score = sum(q.get('score', 0) if q['type'] != 'multipart' else sum(p.get('score', 0) for p in q.get('parts', [])) for q in updated_quiz['questions'])
            for q in updated_quiz['questions']: available_counts[q['type']] += 1

            display_mode = updated_quiz['display_config']['mode']
            if display_mode == 'question_count':
                for q_type, count in updated_quiz['display_config']['parameters'].items():
                    if count > available_counts[q_type]:
                        flash(f"Validation Error: You requested {count} '{q_type}' questions, but only {available_counts[q_type]} are available.", "danger")
                        return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))
            elif display_mode == 'total_score':
                target = updated_quiz['display_config']['target_score']
                if target > total_possible_score:
                    flash(f"Validation Error: Target score of {target} is higher than the total possible score of all questions ({total_possible_score}).", "danger")
                    return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

            # 5. SAVE and redirect if all validation passes.
            save_quiz(quiz_id, updated_quiz)
            flash(f"Quiz '{updated_quiz['name']}' updated successfully!", "success")
            return redirect(url_for('admin.admin_dashboard'))

        except Exception as e:
            # Catch any other errors and provide helpful feedback.
            print("--- A CRITICAL ERROR OCCURRED IN edit_quiz ---")
            traceback.print_exc()
            print("------------------------------------------")
            flash(f"A critical error occurred while saving: {e}", "danger")
            return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

    # Handle GET requests by rendering the editor page.
    return render_template('edit_quiz.html', quiz=quiz)
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        flash("Quiz not found.", "danger")
        return redirect(url_for('admin.admin_dashboard'))


    if request.method == 'POST':
        try:
            # --- START OF THE DEFINITIVE FIX ---
            # 1. Get the entire quiz data from the single 'quizData' form field.
            raw_data = request.form.get('quizData')
            if not raw_data:
                raise ValueError("No quizData submitted by the form. This is a critical error.")
            
            # 2. Parse this JSON string into a Python dictionary.
            form_data = json.loads(raw_data)
            
            # 3. Reconstruct the updated_quiz dictionary directly from this parsed data.
            #    This is much simpler and more reliable than parsing individual fields.
            updated_quiz = {
                'id': quiz_id,
                'pin': quiz['pin'],
                'name': form_data['name'],
                'timer': int(form_data['timer']),
                'is_reviewable': form_data.get('is_reviewable', False),
                'display_config': form_data['display_config'],
                'questions': form_data['questions']
            }
            # --- END OF THE DEFINITIVE FIX ---

            # The validation and saving logic can now proceed exactly as before,
            # because updated_quiz is in the correct format.
            for i, q_data in enumerate(updated_quiz['questions']):
                error = validate_question(q_data, i + 1)
                if error:
                    flash(f"Validation Error: {error}", "danger")
                    return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id, error_q=i))
            
            display_mode = request.form.get('display_mode', 'question_count')
            updated_quiz['display_config'] = {
                'mode': display_mode,
                'parameters': {
                    'multiple-choice': int(request.form.get('rule-multiple-choice', 0)),
                    'short-answer': int(request.form.get('rule-short-answer', 0)),
                    'multiple-select': int(request.form.get('rule-multiple-select', 0)),
                    'multipart': int(request.form.get('rule-multipart', 0))
                },
                'target_score': int(request.form.get('target_score', 0))
            }
            
            form_keys = request.form.keys()
            
            # --- START OF THE NEW, ROBUST PARSING LOGIC ---
            
            # 1. Discover all top-level question prefixes by finding their '-text' fields.
            # This is much more reliable than using '-type'.
            q_prefix_keys = {k.replace('-text', '') for k in form_keys if k.endswith('-text') and k.startswith('question-') and '-part-' not in k}
            all_q_prefixes = sorted(list(q_prefix_keys))
            
            # --- FOR DEBUGGING: Add this print statement to your code ---
            print(f"Discovered {len(all_q_prefixes)} questions to process: {all_q_prefixes}")

            for prefix in all_q_prefixes:
                q_type = request.form.get(f"{prefix}-type")
                
                if not q_type: continue # Skip if for some reason a question has no type
                
                # --- FOR DEBUGGING: Add this print statement ---
                print(f"Processing question with prefix: {prefix}, type: {q_type}")
                
                # Each block creates a complete dictionary for 'new_q'
                if q_type == 'multipart':
                    new_q = {'text': request.form.get(f'{prefix}-text'), 'type': q_type, 'parts': []}
                    part_prefix_keys = {k.replace('-text', '') for k in form_keys if k.endswith('-text') and k.startswith(f'{prefix}-part-')}
                    all_p_prefixes = sorted(list(part_prefix_keys))
                    
                    for p_prefix in all_p_prefixes:
                        part_type = request.form.get(f'{p_prefix}-type')
                        part = {'text': request.form.get(f'{p_prefix}-text'), 'type': part_type, 'score': int(request.form.get(f'{p_prefix}-score'))}
                        if part_type == 'multiple-select':
                            part['answer'] = request.form.getlist(f'{p_prefix}-answer')
                            part['options'] = [opt.strip() for opt in request.form.get(f'{p_prefix}-options', '').splitlines() if opt.strip()]
                        elif part_type == 'multiple-choice':
                            part['answer'] = request.form.get(f'{p_prefix}-answer')
                            part['options'] = [opt.strip() for opt in request.form.get(f'{p_prefix}-options', '').splitlines() if opt.strip()]
                        else: # short-answer
                            part['answer'] = request.form.get(f'{p_prefix}-answer')
                        new_q['parts'].append(part)

                elif q_type == 'multiple-select':
                    new_q = {
                        'text': request.form.get(f'{prefix}-text'), 'type': q_type,
                        'answer': request.form.getlist(f'{prefix}-answer'),
                        'options': [opt.strip() for opt in request.form.get(f'{prefix}-options', '').splitlines() if opt.strip()],
                        'score': int(request.form.get(f'{prefix}-score'))
                    }
                
                elif q_type == 'multiple-choice':
                    new_q = {
                        'text': request.form.get(f'{prefix}-text'), 'type': q_type,
                        'answer': request.form.get(f'{prefix}-answer'),
                        'options': [opt.strip() for opt in request.form.get(f'{prefix}-options', '').splitlines() if opt.strip()],
                        'score': int(request.form.get(f'{prefix}-score'))
                    }

                else: # short-answer
                    new_q = {
                        'text': request.form.get(f'{prefix}-text'), 'type': q_type,
                        'answer': request.form.get(f'{prefix}-answer'),
                        'score': int(request.form.get(f'{prefix}-score'))
                    }
                
                updated_quiz['questions'].append(new_q)
            
            # --- NEW: Add a final check to prevent empty saves ---
            if not updated_quiz['questions'] and any(k.startswith('question-') for k in form_keys):
                 raise ValueError("Question parsing failed: No questions were added to the list, but form data was present.")
            
            # Validation and saving logic
            for i, q_data in enumerate(updated_quiz['questions']):
                error = validate_question(q_data, i + 1)
                if error:
                    flash(f"Validation Error: {error}", "danger")
                    return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id, error_q=i))

            available_counts = defaultdict(int)
            total_possible_score = sum(q.get('score', sum(p.get('score', 0) for p in q.get('parts', []))) for q in updated_quiz['questions'])
            for q in updated_quiz['questions']: available_counts[q['type']] += 1

            if display_mode == 'question_count':
                for q_type, count in updated_quiz['display_config']['parameters'].items():
                    if count > available_counts[q_type]:
                        flash(f"Validation Error: You requested {count} '{q_type}' questions, but only {available_counts[q_type]} are available.", "danger")
                        return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))
            elif display_mode == 'total_score':
                target = updated_quiz['display_config']['target_score']
                if target > total_possible_score:
                    flash(f"Validation Error: Target score of {target} is higher than the total possible score of all questions ({total_possible_score}).", "danger")
                    return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

            save_quiz(quiz_id, updated_quiz)
            flash(f"Quiz '{updated_quiz['name']}' updated successfully!", "success")
            return redirect(url_for('admin.admin_dashboard'))

        except Exception as e:
            # This is the new, detailed error handling block
            print("--- A CRITICAL ERROR OCCURRED ---")
            # This line will print the full, detailed error to your terminal
            traceback.print_exc()
            print("---------------------------------")
            
            flash(f"A critical error occurred. Please check the server console for the full traceback.", "danger")
            flash(f"OS Error Details: {e}", "danger") # Also flash the specific error
            return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))
        # --- END OF DEBUGGING CHANGE ---