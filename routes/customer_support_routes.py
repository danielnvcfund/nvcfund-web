"""
Customer Support Routes
This module handles the routes for the AI customer support feature.
"""
import logging
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for
from flask_login import login_required, current_user
from customer_support import get_answer, load_knowledge_base, save_feedback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
customer_support_bp = Blueprint("customer_support", __name__, url_prefix="/support")

# Load knowledge base at import time
load_knowledge_base()

@customer_support_bp.route("/", methods=["GET"])
def support_index():
    """Main customer support page with chat interface"""
    suggested_questions = [
        "What is NVCToken?",
        "How do I send a SWIFT transfer?",
        "What is a Server-to-Server transfer?",
        "How is NVCT backed?",
        "What is EDI integration?",
        "How do I create an account?",
        "How do I reset my password?",
        "Is my data secure?",
        "What are the fees for transactions?",
        "How do I exchange AFD1 for NVCT?"
    ]
    return render_template("customer_support/index.html", 
                           title="AI Customer Support",
                           suggested_questions=suggested_questions)

@customer_support_bp.route("/ask", methods=["POST"])
def ask_question():
    """API endpoint to handle questions from the chat interface"""
    data = request.json
    question = data.get("question", "").strip()
    
    if not question:
        return jsonify({
            "success": False,
            "message": "Please provide a question"
        }), 400
    
    # Log the question with username if authenticated
    user_identifier = current_user.username if hasattr(current_user, 'username') else "Guest"
    logger.info(f"User {user_identifier} asked: {question}")
    
    # Get answer from knowledge base
    answer = get_answer(question)
    
    return jsonify({
        "success": True,
        "answer": answer,
        "question": question
    })

@customer_support_bp.route("/feedback", methods=["POST"])
def submit_feedback():
    """API endpoint to handle feedback on answers"""
    data = request.json
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()
    helpful = data.get("helpful", False)
    comment = data.get("comment", "").strip()
    
    if not question or not answer:
        return jsonify({
            "success": False,
            "message": "Missing required data"
        }), 400
    
    # Log the feedback
    user_identifier = current_user.username if hasattr(current_user, 'username') else "Guest"
    logger.info(f"Feedback from {user_identifier}: Question: '{question}', Helpful: {helpful}, Comment: '{comment}'")
    
    # Save feedback for future improvements
    save_feedback(question, answer, helpful, comment, user_identifier)
    
    return jsonify({
        "success": True,
        "message": "Thank you for your feedback!"
    })

@customer_support_bp.route("/reload", methods=["GET"])
@login_required
def reload_kb():
    """Reload the knowledge base - admin only"""
    if not current_user.is_admin:
        return redirect(url_for("customer_support.support_index"))
    
    load_knowledge_base()
    return redirect(url_for("customer_support.support_index"))