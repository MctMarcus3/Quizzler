# views/admin.py
import base64
from collections import defaultdict
import json
import traceback
import uuid
import zlib
from flask import Blueprint, render_template, request, redirect, url_for, flash
from data_manager import delete_quiz, get_all_quizzes, get_quiz_by_id, save_quiz
from decorators import admin_required
import pako

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
            'id': quiz_id, 
            'pin': str(uuid.uuid4().int)[:6],
            'name': request.form.get('quiz_name'),
            'timer': quiz_timer,
            'is_reviewable': request.form.get('is_reviewable') == 'on',
            'practice_pin': str(uuid.uuid4().int)[-6:],
            'display_config': {
                'mode': 'question_count',
                'parameters': { 'multiple-choice': 0, 'short-answer': 0, 'multiple-select': 0, 'multipart': 0 },
                'target_score': 10
            },
            'questions': []
        }
        
        save_quiz(quiz_id, new_quiz) # This now saves a file where the filename and internal ID match.
        flash(f"Quiz '{quiz_name}' created. You can now add questions.", "success")
        return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

    return render_template('create_quiz.html')

# --- ADD THIS NEW FUNCTION ---
@admin_bp.route('/change_pin/<quiz_id>', methods=['POST'])
@admin_required
def change_pin(quiz_id):
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        flash("Quiz not found.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    new_pin = request.form.get('new_pin', '').strip()
    if not new_pin:
        flash("New PIN cannot be empty.", "warning")
        return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

    # Validate if the new PIN is already in use
    all_quizzes = get_all_quizzes()
    for q in all_quizzes:
        if q['id'] != quiz_id and q.get('pin') == new_pin:
            flash(f"PIN '{new_pin}' is already in use by another quiz. Please choose a different one.", "danger")
            return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

    quiz['pin'] = new_pin
    save_quiz(quiz_id, quiz)
    flash("Quiz PIN updated successfully.", "success")
    return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))


# --- AND ADD THIS NEW FUNCTION ---
@admin_bp.route('/regenerate_pin/<quiz_id>', methods=['POST'])
@admin_required
def regenerate_pin(quiz_id):
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        flash("Quiz not found.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    quiz['pin'] = str(uuid.uuid4().int)[:6]
    save_quiz(quiz_id, quiz)
    flash(f"New PIN '{quiz['pin']}' generated successfully.", "success")
    return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

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
 
            compressed_data_b64 = request.form.get('quizDataCompressed')
            if not compressed_data_b64:
                raise ValueError("No compressed quiz data submitted.")
            
            compressed_data = base64.b64decode(compressed_data_b64)
            
            # This is the single-line fix.
            # We call zlib.decompress() with NO special arguments.
            # This tells it to expect the standard zlib format, which is what
            # pako sends by default. This resolves the header check error.
            uncompressed_json_bytes = zlib.decompress(compressed_data)
            
            uncompressed_json_string = uncompressed_json_bytes.decode('utf-8')

            form_data = json.loads(uncompressed_json_string)


            
            # 3. Reconstruct the updated_quiz dictionary directly from this parsed data.
            updated_quiz = {
                'id': quiz_id,
                'pin': quiz['pin'],
                'name': form_data['name'],
                'timer': int(form_data['timer']),
                'instructions': form_data.get('instructions', ''),
                'is_reviewable': form_data.get('is_reviewable', False),
                'practice_mode_config': form_data.get('practice_mode_config', {'enabled': False, 'allow_student_selection': False, 'max_questions_limit': 10}),
                'display_config': form_data['display_config'],
                'practice_pin': form_data.get('practice_pin', quiz.get('practice_pin')),
                'questions': form_data['questions'],
                
            }

            # --- MODIFIED VALIDATION LOGIC ---
            validation_messages = []
            error_indices = []

            # Per-Question Validation
            for i, q_data in enumerate(updated_quiz['questions']):
                error = validate_question(q_data, i + 1)
                if error:
                    # Create a message object with text and the question's index
                    validation_messages.append({'text': error, 'index': i})
                    error_indices.append(i)

            # Display Configuration Validation
            available_counts = defaultdict(int)
            total_possible_score = sum(q.get('score', 0) if q['type'] != 'multipart' else sum(p.get('score', 0) for p in q.get('parts', [])) for q in updated_quiz['questions'])
            for q in updated_quiz['questions']: available_counts[q['type']] += 1

            display_mode = updated_quiz['display_config']['mode']
            if display_mode == 'question_count':
                for q_type, count in updated_quiz['display_config']['parameters'].items():
                    if count > available_counts[q_type]:
                        # General errors have no index
                        validation_messages.append({'text': f"Display Error: You requested {count} '{q_type}' questions, but only {available_counts[q_type]} are available."})
            elif display_mode == 'total_score':
                target = updated_quiz['display_config']['target_score']
                if target > total_possible_score:
                    validation_messages.append({'text': f"Display Error: Target score of {target} is higher than the total possible score of all questions ({total_possible_score})."})

            if validation_messages:
                # Instead of flashing, pass the structured errors and indices to the template
                return render_template('edit_quiz.html', quiz=updated_quiz, validation_errors=validation_messages, error_indices=error_indices)
            
            save_quiz(quiz_id, updated_quiz)
            flash(f"Quiz '{updated_quiz['name']}' updated successfully!", "success")
            return redirect(url_for('admin.admin_dashboard'))

        except Exception as e:
            # Catch any other errors and provide helpful feedback.
            print("--- A CRITICAL ERROR OCCURRED IN edit_quiz ---")
            traceback.print_exc()
            print("------------------------------------------")
            flash(f"A critical error occurred while saving: {e}", "danger")
            return render_template('edit_quiz.html', quiz=quiz)

    # Handle GET requests by rendering the editor page.
    return render_template('edit_quiz.html', quiz=quiz)

# --- ADD THIS NEW FUNCTION ---
@admin_bp.route('/delete/<quiz_id>', methods=['POST'])
@admin_required
def delete_quiz_bank(quiz_id):
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        flash("Quiz not found.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    pin_confirm = request.form.get('pin_confirm')
    if pin_confirm == quiz.get('pin'):
        if delete_quiz(quiz_id):
            flash(f"Quiz '{quiz['name']}' has been permanently deleted.", "success")
        else:
            flash("An error occurred while trying to delete the quiz file.", "danger")
    else:
        flash("Incorrect PIN. Deletion cancelled.", "warning")

    return redirect(url_for('admin.admin_dashboard'))