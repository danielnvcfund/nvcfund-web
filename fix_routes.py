"""
Fix Route Inconsistencies Script
This script fixes the routing inconsistencies in main_routes.py for transaction editing and cancellation
by aligning the route definitions with the URL patterns used in templates.
"""

import os
import re
import fileinput
from pathlib import Path

def find_route_in_file(filepath, route_pattern):
    """Find route patterns in file"""
    with open(filepath, 'r') as file:
        content = file.read()
        matches = re.findall(route_pattern, content)
        return matches

def fix_main_routes():
    """Fix the routing in main_routes.py"""
    file_path = "routes/main_routes.py"
    
    # Check current state
    print(f"Checking {file_path}...")
    edit_route = find_route_in_file(file_path, r"@main\.route\(['\"](.+?)/edit.+?\)")
    cancel_route = find_route_in_file(file_path, r"@main\.route\(['\"](.+?)/cancel.+?\)")
    
    print(f"Current edit route pattern: {edit_route}")
    print(f"Current cancel route pattern: {cancel_route}")
    
    # Read the file content
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Define the patterns to find and replace
    edit_pattern = r"@main\.route\(['\"](.+?)/edit/(.+?)['\"]"
    cancel_pattern = r"@main\.route\(['\"](.+?)/cancel/(.+?)['\"]"
    
    # Replacement patterns - make all main routes consistent with web.main prefix
    edit_replacement = r"@main.route('/transaction/edit/\2'"
    cancel_replacement = r"@main.route('/transaction/cancel/\2'"
    
    # Apply replacements
    modified_content = re.sub(edit_pattern, edit_replacement, content)
    modified_content = re.sub(cancel_pattern, cancel_replacement, modified_content)
    
    # Write the modified content back to the file
    with open(file_path, 'w') as file:
        file.write(modified_content)
    
    print("Routes have been fixed for consistency.")
    
    # Verify the changes
    edit_route_after = find_route_in_file(file_path, r"@main\.route\(['\"](.+?)/edit.+?\)")
    cancel_route_after = find_route_in_file(file_path, r"@main\.route\(['\"](.+?)/cancel.+?\)")
    
    print(f"New edit route pattern: {edit_route_after}")
    print(f"New cancel route pattern: {cancel_route_after}")

if __name__ == "__main__":
    fix_main_routes()