#!/usr/bin/env python3
"""
Script to fix URL redirections in the payment processor routes
"""

import re

# Define the pattern to find and the replacement
find_pattern = r"return redirect\(url_for\('main\.index'\)\)"
replace_with = "return redirect(url_for(INDEX_ROUTE))"

# Read the file
with open('routes/payment_processor_routes.py', 'r') as file:
    content = file.read()

# Replace all occurrences
updated_content = re.sub(find_pattern, replace_with, content)

# Write back to the file
with open('routes/payment_processor_routes.py', 'w') as file:
    file.write(updated_content)

print("Fixed all main.index redirects in payment_processor_routes.py")
