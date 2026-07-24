import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import bcrypt
import random

app = Flask(__name__)
CORS(app)  # Allow frontend to communicate with backend

# MySQL Configuration
# (Change these if your local MySQL setup is different)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Nikhil@PC-SQL-ROOT#121',
    'database': 'spxbank'
}

# In-memory OTP store for Phase 1 (Key: email, Value: {otp, action})
# In a real production app, this goes to MySQL or Redis.
OTP_STORE = {}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('firstName')
    last_name = data.get('lastName')

    if not all([username, email, password, first_name, last_name]):
        return jsonify({'success': False, 'message': 'Missing fields'}), 400

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if username or email exists
        cursor.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Username or email already exists'}), 409
        
        account_number = f"#8849-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"

        sql = """
        INSERT INTO users (username, email, password_hash, first_name, last_name, account_number, balance) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (username, email, hashed_pw, first_name, last_name, account_number, 25000.00))
        conn.commit()

        # Get the new user to return
        user_obj = {
            'name': f"{first_name} {last_name}",
            'email': email,
            'accountType': 'Savings Account',
            'accountNumber': account_number,
            'balance': '25,000.00'
        }
        return jsonify({'success': True, 'user': user_obj})
        
    except Exception as e:
        print(f"DB Error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            user_obj = {
                'name': f"{user['first_name']} {user['last_name']}",
                'email': user['email'],
                'accountType': 'Savings Account',
                'accountNumber': user['account_number'],
                'balance': str(user['balance'])
            }
            return jsonify({'success': True, 'user': user_obj, 'email': user['email']})
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
    except Exception as e:
        print(f"DB Error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    action = data.get('action')
    # Use frontend provided OTP for now to keep exact modal behavior as requested, 
    # though in phase 2 backend should generate it.
    otp = data.get('otp') 
    
    if not email or not otp:
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    # Store OTP in memory mapping to this email
    OTP_STORE[email] = {'otp': otp, 'action': action}

    # Here we would use smtplib to send the real email.
    # For local testing, we just print it.
    print(f"--- EMAIL DISPATCH SIMULATOR ---")
    print(f"To: {email}")
    print(f"Subject: Bank Portal Verification")
    print(f"OTP: {otp}")
    print(f"--------------------------------")

    return jsonify({'success': True, 'requiresFrontendApiFallback': False, 'message': 'OTP sent'})

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')

    record = OTP_STORE.get(email)
    if record and record['otp'] == otp:
        # Clear the OTP once used
        del OTP_STORE[email]
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid OTP'})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
