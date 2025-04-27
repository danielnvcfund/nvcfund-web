#!/usr/bin/env python3
"""
Script to check template files referenced in payment_processor_routes.py
"""

import re
import os

# Define the templates directory
templates_dir = 'templates'

# Define a regex pattern to extract render_template calls
render_pattern = r"render_template\(\s*'([^']+)'"

# Read the routes file
template_files = []
with open('routes/payment_processor_routes.py', 'r') as file:
    content = file.read()
    # Find all render_template calls
    matches = re.findall(render_pattern, content)
    template_files.extend(matches)

# Check each template file
missing_files = []
for template in template_files:
    template_path = os.path.join(templates_dir, template)
    if not os.path.exists(template_path):
        missing_files.append(template_path)

if missing_files:
    print("The following template files are missing:")
    for file in missing_files:
        print(f"  - {file}")
else:
    print("All template files exist!")

