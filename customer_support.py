"""
Customer Support Module
This module provides AI-powered customer support functionality using a knowledge base
built from platform documentation.
"""

import os
import re
import logging
from flask import current_app
import markdown
from bs4 import BeautifulSoup

# Set up logging
logger = logging.getLogger(__name__)

class CustomerSupportKnowledgeBase:
    """Knowledge base for customer support queries"""
    
    def __init__(self):
        """Initialize the knowledge base"""
        self.articles = []
        self.faq_data = {}
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Load all documentation into the knowledge base"""
        try:
            # Load HTML guides
            self._load_html_guides()
            
            # Load markdown files
            self._load_markdown_files()
            
            # Load PDF content summaries (if available)
            self._load_pdf_summaries()
            
            # Load FAQ data
            self._load_faq_data()
            
            logger.info(f"Knowledge base loaded with {len(self.articles)} articles")
        except Exception as e:
            logger.error(f"Error loading knowledge base: {str(e)}")
    
    def _load_html_guides(self):
        """Load HTML guides from static/docs directory"""
        docs_dir = os.path.join(os.getcwd(), 'static', 'docs')
        if not os.path.exists(docs_dir):
            logger.warning(f"HTML docs directory not found: {docs_dir}")
            return
            
        for filename in os.listdir(docs_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(docs_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse HTML to extract text
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Get title
                    title_tag = soup.find('title')
                    title = title_tag.text if title_tag else filename.replace('_', ' ').replace('.html', '').title()
                    
                    # Extract text content, removing scripts and styles
                    for script in soup(["script", "style"]):
                        script.extract()
                    
                    text = soup.get_text(separator=' ', strip=True)
                    
                    # Clean up text
                    text = re.sub(r'\s+', ' ', text)
                    
                    # Add to knowledge base
                    self.articles.append({
                        'title': title,
                        'content': text,
                        'source': f'HTML Guide: {filename}',
                        'type': 'html',
                        'filename': filename
                    })
                    
                    logger.debug(f"Loaded HTML guide: {filename}")
                except Exception as e:
                    logger.error(f"Error loading HTML guide {filename}: {str(e)}")
    
    def _load_markdown_files(self):
        """Load markdown files from docs directory"""
        docs_dir = os.path.join(os.getcwd(), 'docs')
        if not os.path.exists(docs_dir):
            logger.warning(f"Markdown docs directory not found: {docs_dir}")
            return
            
        for filename in os.listdir(docs_dir):
            if filename.endswith('.md') and not filename.startswith('README'):
                file_path = os.path.join(docs_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Convert markdown to HTML, then extract text
                    html = markdown.markdown(content)
                    soup = BeautifulSoup(html, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                    
                    # Clean up text
                    text = re.sub(r'\s+', ' ', text)
                    
                    # Get title from first heading or filename
                    title = filename.replace('_', ' ').replace('.md', '').title()
                    
                    # Add to knowledge base
                    self.articles.append({
                        'title': title,
                        'content': text,
                        'source': f'Documentation: {filename}',
                        'type': 'markdown',
                        'filename': filename
                    })
                    
                    logger.debug(f"Loaded markdown file: {filename}")
                except Exception as e:
                    logger.error(f"Error loading markdown file {filename}: {str(e)}")
    
    def _load_pdf_summaries(self):
        """Load PDF summaries if available"""
        # This would require PDF text extraction which is complex
        # For now, we'll use a placeholder for future implementation
        pdf_summaries_dir = os.path.join(os.getcwd(), 'pdf_summaries')
        if not os.path.exists(pdf_summaries_dir):
            return
            
        # Code for loading PDF summaries would go here
        pass
    
    def _load_faq_data(self):
        """Load FAQ data"""
        # Hardcoded FAQ data for common questions
        self.faq_data = {
            # Authentication
            "How do I reset my password?": "To reset your password, click on the 'Forgot Password' link on the login page. You will be prompted to enter your email address. A password reset link will be sent to your email.",
            
            "How do I create an account?": "New accounts can only be created by invitation. If you need an account, please contact your financial institution administrator or send a request to support@nvcplatform.net.",
            
            # Payments
            "How do I send a SWIFT transfer?": "To send a SWIFT transfer, log in to your account, navigate to 'Payments' > 'New SWIFT Transfer'. Fill in the required details including recipient bank information, account details, amount, and payment purpose. Submit the form to initiate the transfer.",
            
            "What is a Server-to-Server transfer?": "Server-to-Server (S2S) transfers are secure, high-volume transactions between financial institutions. They enable direct integration between banking systems with minimal latency. This feature requires explicit authorization and setup by NVC Global.",
            
            # NVCT Token
            "What is NVCToken?": "NVCToken (NVCT) is a fully-backed stablecoin pegged to the US Dollar (1 NVCT = 1 USD). It serves as the native token of the NVC Banking Platform, providing a stable store of value and settlement mechanism within the global financial ecosystem.",
            
            "How is NVCT backed?": "NVCT is fully backed by over $10 trillion USD in audited assets managed by NVC Fund Holding Trust, including verified financial statements, investments, cash equivalents, precious metals, and historical banking assets.",
            
            # EDI
            "What is EDI integration?": "Electronic Data Interchange (EDI) is a system for standardized electronic fund transfers with banks and financial institutions. The NVC platform supports multiple EDI formats including X12 and EDIFACT, enabling secure, automated financial transactions.",
            
            # Blockchain
            "How does blockchain settlement work?": "Blockchain settlement on the NVC platform uses smart contracts on the Ethereum network to provide secure, transparent transaction settlement. When a transfer is initiated, funds are securely moved through the settlement contract, creating an immutable record on the blockchain.",
            
            # General
            "Who do I contact for support?": "For technical support, contact our team at support@nvcplatform.net or call +1 (555) 123-4567. Support hours are Monday-Friday, 9am-5pm ET.",
            
            "Is my data secure?": "Yes, the NVC Banking Platform uses enterprise-grade security measures including encryption, multi-factor authentication, and secure data storage. All transactions are logged and monitored for suspicious activity."
        }
        
        # Convert FAQ items to knowledge base articles
        for question, answer in self.faq_data.items():
            self.articles.append({
                'title': question,
                'content': f"{question} {answer}",
                'source': 'FAQ',
                'type': 'faq',
                'is_faq': True
            })
        
        logger.debug(f"Loaded {len(self.faq_data)} FAQ items")
    
    def search(self, query):
        """
        Search the knowledge base for relevant information
        
        Args:
            query (str): The search query
            
        Returns:
            list: Relevant articles sorted by relevance
        """
        query = query.lower()
        results = []
        
        # First check exact matches in FAQ
        for question, answer in self.faq_data.items():
            if query in question.lower():
                results.append({
                    'title': question,
                    'content': answer,
                    'source': 'FAQ',
                    'relevance': 1.0 if query == question.lower() else 0.9,
                    'is_faq': True
                })
        
        # Then check knowledge base articles
        for article in self.articles:
            if 'is_faq' in article and article['is_faq']:
                continue  # Skip FAQ items already checked
                
            # Simple relevance scoring based on keyword matching
            title_score = 0
            content_score = 0
            
            # Check title
            if query in article['title'].lower():
                title_score = 0.8
            
            # Check content
            content_lower = article['content'].lower()
            if query in content_lower:
                # Count occurrences for relevance
                occurrences = content_lower.count(query)
                content_score = min(0.6, 0.1 * occurrences)
            
            # Calculate overall relevance
            relevance = max(title_score, content_score)
            
            # If relevant, add to results
            if relevance > 0:
                # Extract a snippet around the query
                snippet = self._extract_snippet(article['content'], query)
                
                results.append({
                    'title': article['title'],
                    'content': snippet,
                    'source': article['source'],
                    'relevance': relevance,
                    'is_faq': False
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance'], reverse=True)
        
        return results[:5]  # Return top 5 results
    
    def _extract_snippet(self, content, query, chars=200):
        """Extract a relevant snippet from content around the query"""
        query = query.lower()
        content_lower = content.lower()
        
        # Find position of query
        pos = content_lower.find(query)
        if pos == -1:
            # If query not found, return beginning of content
            return content[:chars] + "..." if len(content) > chars else content
        
        # Calculate snippet start and end
        start = max(0, pos - chars // 2)
        end = min(len(content), pos + len(query) + chars // 2)
        
        # Adjust to avoid cutting words
        while start > 0 and content[start] != ' ':
            start -= 1
        
        while end < len(content) and content[end] != ' ':
            end += 1
        
        # Create snippet
        snippet = content[start:end]
        
        # Add ellipsis if needed
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def get_answer(self, query):
        """
        Generate an answer for a user query
        
        Args:
            query (str): The user's question
            
        Returns:
            dict: Response with answer and sources
        """
        # Search for relevant information
        results = self.search(query)
        
        if not results:
            return {
                'answer': "I'm sorry, I don't have information on that topic. Please contact our support team for assistance.",
                'sources': []
            }
        
        # Check if we have a direct FAQ match
        for result in results:
            if result.get('is_faq') and result['relevance'] > 0.8:
                return {
                    'answer': result['content'],
                    'sources': [{'title': result['title'], 'source': 'FAQ'}]
                }
        
        # Otherwise, construct answer from top results
        answer_parts = []
        sources = []
        
        for result in results[:3]:  # Use top 3 results
            answer_parts.append(result['content'])
            sources.append({
                'title': result['title'],
                'source': result['source']
            })
        
        combined_answer = " ".join(answer_parts)
        
        # Limit answer length
        if len(combined_answer) > 500:
            combined_answer = combined_answer[:497] + "..."
        
        return {
            'answer': combined_answer,
            'sources': sources
        }


# Singleton instance
_knowledge_base = None

def get_knowledge_base():
    """Get or create the knowledge base instance"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = CustomerSupportKnowledgeBase()
    return _knowledge_base


def get_answer(query):
    """
    Get an answer for a customer support query
    
    Args:
        query (str): The customer's question
        
    Returns:
        dict: Response with answer and sources
    """
    kb = get_knowledge_base()
    return kb.get_answer(query)