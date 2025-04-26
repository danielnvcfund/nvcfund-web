"""
Customer Support Module
This module provides AI-powered customer support functionality through
a knowledge base built from existing documentation.
"""
import os
import re
import json
import logging
import datetime
from typing import List, Dict, Any
from flask import current_app
from bs4 import BeautifulSoup
import markdown

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Paths
STATIC_DOCS_PATH = "static/docs"
DOCUMENTATION_PATH = "templates/documentation/docs"
FAQ_PATH = "templates/documentation/faq"
FEEDBACK_PATH = "data/support_feedback"

# Knowledge base
articles = []

def load_knowledge_base() -> None:
    """Load knowledge base from documentation sources"""
    global articles
    articles = []
    
    # Create feedback directory if not exists
    os.makedirs(FEEDBACK_PATH, exist_ok=True)
    
    # Load HTML guides from static/docs
    for filename in os.listdir(STATIC_DOCS_PATH):
        if filename.endswith(".html"):
            try:
                logger.debug(f"Loaded HTML guide: {filename}")
                filepath = os.path.join(STATIC_DOCS_PATH, filename)
                content = extract_text_from_html(filepath)
                articles.append({
                    "source": f"guide:{filename}",
                    "title": filename.replace("_", " ").replace(".html", "").title(),
                    "content": content
                })
            except Exception as e:
                logger.error(f"Error loading HTML guide {filename}: {str(e)}")
    
    # Load markdown files from documentation path
    try:
        if os.path.exists(DOCUMENTATION_PATH):
            for filename in os.listdir(DOCUMENTATION_PATH):
                if filename.endswith(".md"):
                    try:
                        logger.debug(f"Loaded markdown file: {filename}")
                        filepath = os.path.join(DOCUMENTATION_PATH, filename)
                        with open(filepath, 'r') as f:
                            content = f.read()
                        articles.append({
                            "source": f"doc:{filename}",
                            "title": filename.replace("_", " ").replace(".md", "").title(),
                            "content": content
                        })
                    except Exception as e:
                        logger.error(f"Error loading markdown file {filename}: {str(e)}")
    except Exception as e:
        logger.error(f"Error accessing documentation path: {str(e)}")
    
    # Load FAQ items
    try:
        if os.path.exists(FAQ_PATH):
            faq_file = os.path.join(FAQ_PATH, "faq.json")
            if os.path.exists(faq_file):
                with open(faq_file, 'r') as f:
                    faq_data = json.load(f)
                
                for item in faq_data:
                    try:
                        articles.append({
                            "source": "faq",
                            "title": item.get("question", ""),
                            "content": item.get("answer", "")
                        })
                    except Exception as e:
                        logger.error(f"Error loading FAQ item: {str(e)}")
                
                logger.debug(f"Loaded {len(faq_data)} FAQ items")
    except Exception as e:
        logger.error(f"Error loading FAQ: {str(e)}")
    
    logger.info(f"Knowledge base loaded with {len(articles)} articles")

def extract_text_from_html(filepath: str) -> str:
    """Extract readable text content from HTML file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from HTML {filepath}: {str(e)}")
        return ""

def search_knowledge_base(query: str) -> List[Dict[str, Any]]:
    """
    Search the knowledge base for relevant articles
    Returns list of matched articles sorted by relevance
    """
    matches = []
    
    # Clean the query
    query = query.lower().strip()
    query_words = set(re.findall(r'\w+', query))
    
    # Skip if query is too short
    if len(query_words) < 1:
        return []
    
    # Search through articles
    for article in articles:
        title = article.get("title", "").lower()
        content = article.get("content", "").lower()
        
        # Calculate a simple relevance score
        title_match = sum(1 for word in query_words if word in title)
        content_match = sum(1 for word in query_words if word in content)
        
        # Weight title matches more heavily
        score = (title_match * 3) + content_match
        
        # Only include if there's some relevance
        if score > 0:
            matches.append({
                "article": article,
                "score": score
            })
    
    # Sort by score (descending)
    matches.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top matches
    return [match["article"] for match in matches[:3]]

def get_answer(question: str) -> str:
    """Generate an answer based on the knowledge base"""
    try:
        # Search for relevant articles
        matches = search_knowledge_base(question)
        
        if not matches:
            return "I don't have specific information about that topic yet. Please try asking about our payment systems, SWIFT transfers, server-to-server integration, EDI, or NVC Tokenomics."
        
        # Construct an answer from the matched articles
        answer_parts = []
        
        # Add introduction
        if len(matches) == 1:
            answer_parts.append("Based on our documentation, here's what I found:")
        else:
            answer_parts.append(f"I found {len(matches)} relevant pieces of information:")
        
        # Add content from matched articles
        for i, match in enumerate(matches):
            title = match.get("title", "")
            content = match.get("content", "")
            
            # Limit content length for readability
            max_length = 500
            if len(content) > max_length:
                # Try to find a sensible cutoff point
                cutoff = content.rfind('. ', 0, max_length)
                if cutoff == -1:
                    cutoff = max_length
                content = content[:cutoff+1] + "..."
            
            # Format as markdown for better presentation
            answer_parts.append(f"\n\n**{title}**\n{content}")
        
        # Add prompt for feedback
        answer_parts.append("\n\n*Was this answer helpful? Please use the feedback buttons below to let us know.*")
        
        return "\n".join(answer_parts)
    
    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}")
        return "I'm having trouble processing your question right now. Please try again or contact support for assistance."

def save_feedback(question: str, answer: str, helpful: bool, comment: str, user: str) -> None:
    """Save user feedback for later analysis and improvement"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        feedback_id = f"{timestamp}_{user}"
        
        feedback_data = {
            "id": feedback_id,
            "timestamp": timestamp,
            "user": user,
            "question": question,
            "answer": answer,
            "helpful": helpful,
            "comment": comment
        }
        
        # Save to file
        filename = os.path.join(FEEDBACK_PATH, f"feedback_{feedback_id}.json")
        with open(filename, 'w') as f:
            json.dump(feedback_data, f, indent=2)
        
        logger.info(f"Saved feedback {feedback_id}")
    
    except Exception as e:
        logger.error(f"Error saving feedback: {str(e)}")

# Initialize the knowledge base when module is loaded
# This will be called again in the blueprint initialization
if not articles:
    try:
        load_knowledge_base()
    except Exception as e:
        logger.error(f"Error initializing knowledge base: {str(e)}")