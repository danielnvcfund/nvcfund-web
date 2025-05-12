from app import app  # noqa: F401
from flask import send_from_directory
import os

def generate_custody_agreement():
    """Check if custody agreement exists and generate if needed"""
    from generate_custody_agreement import generate_custody_agreement as gen_agreement
    
    # Path to the static PDF file
    static_file_path = os.path.join(os.getcwd(), 'static', 'documents', 'NVC_Fund_Bank_Custody_Agreement.pdf')
    
    # If the file doesn't exist, generate it
    if not os.path.exists(static_file_path):
        static_file_path = gen_agreement()
    
    return static_file_path

@app.route('/get-custody-agreement')
def serve_agreement():
    """Serve the custody agreement PDF directly"""
    # Ensure file exists
    generate_custody_agreement()
    
    # Serve the file directly
    return send_from_directory('static/documents', 'NVC_Fund_Bank_Custody_Agreement.pdf', 
                              mimetype='application/pdf', as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)