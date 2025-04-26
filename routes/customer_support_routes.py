"""
Customer Support Routes
This module provides routes for the AI customer support feature.
"""

import logging
from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from customer_support import get_answer

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
customer_support_bp = Blueprint('customer_support', __name__, url_prefix='/support')

@customer_support_bp.route('/')
@login_required
def support_index():
    """Customer support main page"""
    return render_template(
        'customer_support/index.html',
        is_admin=current_user.is_admin if hasattr(current_user, 'is_admin') else False
    )

@customer_support_bp.route('/api/ask', methods=['POST'])
@login_required
def ask_question():
    """API endpoint to ask a question"""
    data = request.get_json()
    
    if not data or 'question' not in data:
        return jsonify({
            'error': 'Invalid request, question is required'
        }), 400
    
    question = data['question']
    
    # Validate question
    if not question.strip():
        return jsonify({
            'error': 'Question cannot be empty'
        }), 400
    
    # Log the question for future training and improvement
    logger.info(f"User {current_user.username} asked: {question}")
    
    try:
        # Get answer from knowledge base
        response = get_answer(question)
        
        return jsonify({
            'answer': response['answer'],
            'sources': response['sources']
        })
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        return jsonify({
            'error': 'Failed to process question',
            'message': str(e)
        }), 500

@customer_support_bp.route('/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Submit feedback on an answer"""
    data = request.get_json()
    
    if not data or 'question' not in data or 'answer' not in data or 'helpful' not in data:
        return jsonify({
            'error': 'Invalid feedback data'
        }), 400
    
    question = data['question']
    answer = data['answer']
    helpful = data['helpful']
    feedback = data.get('feedback', '')
    
    # Log feedback for future improvements
    logger.info(f"Feedback from {current_user.username}: Question: {question}, Helpful: {helpful}, Comment: {feedback}")
    
    return jsonify({
        'status': 'success',
        'message': 'Thank you for your feedback'
    })