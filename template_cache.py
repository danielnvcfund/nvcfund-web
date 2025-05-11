"""
Template Cache for NVC Banking Platform

This module provides Flask Jinja2 template caching to improve rendering performance.
"""

import os
import logging
from flask import Flask
from jinja2 import FileSystemLoader, ChoiceLoader, BytecodeCache
import hashlib
import tempfile

logger = logging.getLogger(__name__)

class TemplateBytecodeCache(BytecodeCache):
    """Bytecode cache for Jinja2 templates"""
    
    def __init__(self, directory=None, pattern='__jinja2_%s.cache'):
        if directory is None:
            directory = tempfile.gettempdir()
        self.directory = directory
        self.pattern = pattern
        self.enabled = True
        
        # Try to create the cache directory if it doesn't exist
        try:
            if not os.path.exists(self.directory):
                os.makedirs(self.directory)
        except Exception as e:
            logger.warning(f"Could not create template cache directory: {str(e)}")
            self.enabled = False
    
    def _get_cache_filename(self, bucket):
        """Get filename for cache bucket"""
        if not self.enabled:
            return None
            
        hash_str = hashlib.sha1(bucket.key.encode('utf-8')).hexdigest()
        return os.path.join(self.directory, self.pattern % hash_str)
    
    def load_bytecode(self, bucket):
        """Load bytecode from cache"""
        if not self.enabled:
            return
            
        filename = self._get_cache_filename(bucket)
        if filename and os.path.exists(filename):
            try:
                with open(filename, 'rb') as f:
                    bucket.bytecode_from_string(f.read())
            except Exception as e:
                logger.debug(f"Error loading template bytecode: {str(e)}")
    
    def dump_bytecode(self, bucket):
        """Save bytecode to cache"""
        if not self.enabled:
            return
            
        filename = self._get_cache_filename(bucket)
        if filename:
            try:
                with open(filename, 'wb') as f:
                    f.write(bucket.bytecode_to_string())
            except Exception as e:
                logger.debug(f"Error saving template bytecode: {str(e)}")
    
    def clear(self):
        """Clear the cache"""
        if not self.enabled or not os.path.exists(self.directory):
            return
            
        for filename in os.listdir(self.directory):
            if filename.startswith('__jinja2_'):
                try:
                    os.remove(os.path.join(self.directory, filename))
                except (IOError, OSError) as e:
                    logger.debug(f"Error removing template cache file: {str(e)}")


def enable_template_caching(app):
    """
    Enable template caching for a Flask application
    
    Args:
        app (Flask): Flask application
    """
    if not isinstance(app, Flask):
        logger.error("Not a Flask application")
        return False
        
    try:
        # Create template bytecode cache
        cache_dir = os.path.join(tempfile.gettempdir(), 'nvc_template_cache')
        bytecode_cache = TemplateBytecodeCache(directory=cache_dir)
        
        # Enable bytecode caching
        app.jinja_env.bytecode_cache = bytecode_cache
        
        # Auto reload only in debug mode
        app.jinja_env.auto_reload = app.debug
        
        logger.info(f"Template caching enabled with bytecode cache at {cache_dir}")
        return True
    except Exception as e:
        logger.error(f"Error enabling template caching: {str(e)}")
        return False


def clear_template_cache(app):
    """Clear the template cache"""
    if not isinstance(app, Flask):
        logger.error("Not a Flask application")
        return False
        
    try:
        if hasattr(app.jinja_env, 'bytecode_cache'):
            app.jinja_env.bytecode_cache.clear()
            logger.info("Template cache cleared")
            return True
        return False
    except Exception as e:
        logger.error(f"Error clearing template cache: {str(e)}")
        return False