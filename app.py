import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import bcrypt
import random
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uuid

load_dotenv()

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'database': os.environ.get('DB_NAME', 'spxbank')
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_email_template(action, first_name, otp):
    subject = "Login Verification OTP"
    heading = "Verify your SPX Bank login"
    body_desc = "We received a request to sign in to your SPX Bank Netbanking account. Please enter the code below to continue."
    notice = "If you did not attempt to log in, please disregard this email and change your password immediately, as your account may be at risk."

    if action == 'REGISTER':
        subject = "Email Verification OTP"
        heading = "Verify your SPX Bank sign-up"
        body_desc = "We received a request to create an SPX Bank Netbanking account. Please enter the code below in the window where you started registration."
        notice = "If you did not attempt to sign up but received this email, please disregard it."
    elif action == 'RESET_PASSWORD':
        subject = "Password Reset OTP"
        heading = "Reset your SPX Bank password"
        body_desc = "We received a request to reset the password for your SPX Bank Netbanking account. Please enter the code below to continue."
        notice = "If you did not request a password reset, please disregard this email. Your password will remain unchanged unless this code is used."

    plain_text = f"{heading}\n\n{body_desc}\n\nVerification Code: {otp}\n\n{notice}\n\nThis code will remain active for 5 minutes. Never share this code with anyone, including SPX Bank employees.\n\nRef: {uuid.uuid4()}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f8f9fa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <div style="background-color: #f8f9fa; padding: 40px 20px;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); padding: 40px; border: 1px solid #eaeaea;">
                
                <div style="text-align: center; margin-bottom: 30px;">
                    <img src="cid:logo_image" alt="" style="height: 36px; vertical-align: middle; margin-right: 8px;">
                    <span style="color: #111827; font-size: 24px; font-weight: 800; vertical-align: middle; letter-spacing: -0.5px;">SPX Bank</span>
                </div>
                
                <h1 style="color: #111827; font-size: 20px; font-weight: 700; margin-top: 0; margin-bottom: 16px; text-align: center;">
                    {heading}
                </h1>
                
                <p style="color: #4b5563; font-size: 15px; line-height: 1.6; margin-bottom: 30px; text-align: center;">
                    {body_desc}
                </p>
                
                <div style="background-color: #f4f5f7; border: 1px solid #eaeaea; padding: 24px; text-align: center; border-radius: 6px; margin-bottom: 30px;">
                    <div style="font-size: 32px; font-weight: bold; color: #111827; letter-spacing: 8px; margin-left: 8px;">
                        {otp}
                    </div>
                </div>
                
                <p style="color: #6b7280; font-size: 13px; line-height: 1.5; margin-bottom: 0; text-align: center;">
                    {notice} This code will remain active for 5 minutes. Never share this code with anyone, including SPX Bank employees.
                </p>
                
                <hr style="border: none; border-top: 1px solid #eaeaea; margin: 30px 0;">
                
                <div style="text-align: center; color: #9ca3af; font-size: 12px; line-height: 1.5;">
                    <p style="margin: 0 0 8px 0;">SPX Bank, secure Netbanking built for you.</p>
                    <p style="margin: 0;">&copy; 2026 SPX Bank. All rights reserved.</p>
                </div>
                
            </div>
        </div>
        <div style="display: none; max-height: 0px; overflow: hidden;">{uuid.uuid4()}</div>
    </body>
    </html>
    """
    return subject, html_content, plain_text

def send_real_email(to_email, subject, html_body, plain_text):
    try:
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 465))
        smtp_user = os.environ.get('SMTP_USER')
        smtp_pass = os.environ.get('SMTP_PASS')

        if not smtp_user or not smtp_pass:
            print("WARNING: SMTP credentials not set. Simulated email:")
            print(f"To: {to_email}\nSubject: {subject}\nBody: HTML Content rendered")
            return True

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = f"SPX Bank <{smtp_user}>"
        msg['To'] = to_email
        msg.set_content(plain_text)
        msg.add_alternative(html_body, subtype='html')

        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'images', 'logo.png')
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    img_data = f.read()
                msg.get_payload()[1].add_related(img_data, 'image', 'png', cid='<logo_image>')
        except Exception as e:
            print(f"Failed to attach logo: {e}")

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

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

        user_obj = {
            'username': username,
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

        if not user:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

        # Check lockout
        now = datetime.now()
        if user['lockout_until'] and user['lockout_until'] > now:
            remaining = int((user['lockout_until'] - now).total_seconds())
            return jsonify({'success': False, 'lockout': True, 'remaining_seconds': remaining, 'message': f'Account locked. Please wait {remaining} seconds.'}), 423

        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # Reset attempts on success
            cursor.execute("UPDATE users SET failed_attempts=0, lockout_until=NULL WHERE id=%s", (user['id'],))
            conn.commit()

            user_obj = {
                'username': user['username'],
                'name': f"{user['first_name']} {user['last_name']}",
                'email': user['email'],
                'accountType': 'Savings Account',
                'accountNumber': user['account_number'],
                'balance': str(user['balance'])
            }
            return jsonify({'success': True, 'user': user_obj, 'email': user['email']})
        else:
            # Failed attempt
            attempts = user['failed_attempts'] + 1
            if attempts >= 3:
                lockout_time = now + timedelta(seconds=30)
                cursor.execute("UPDATE users SET failed_attempts=%s, lockout_until=%s WHERE id=%s", (attempts, lockout_time, user['id']))
                conn.commit()
                return jsonify({'success': False, 'lockout': True, 'remaining_seconds': 30, 'message': 'Account locked. Please wait 30 seconds.'}), 423
            else:
                cursor.execute("UPDATE users SET failed_attempts=%s WHERE id=%s", (attempts, user['id']))
                conn.commit()
                remaining = 3 - attempts
                msg = f'Incorrect password. {remaining} attempt{"s" if remaining > 1 else ""} remaining.'
                return jsonify({'success': False, 'lockout': False, 'attempts_remaining': remaining, 'message': msg}), 401

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
    frontend_username = data.get('username')
    
    if not email:
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    otp = str(random.randint(100000, 999999))
    expires_at = datetime.now() + timedelta(minutes=5)
    
    first_name = frontend_username if frontend_username else "Customer"

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT first_name, username FROM users WHERE email=%s", (email,))
        user_record = cursor.fetchone()
        
        if user_record:
            if user_record.get('first_name'):
                first_name = user_record['first_name']
            elif user_record.get('username'):
                first_name = user_record['username']

        cursor.execute("INSERT INTO otps (email, otp, expires_at) VALUES (%s, %s, %s)", (email, otp, expires_at))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

    subject, html_body, plain_text = get_email_template(action, first_name, otp)
    send_real_email(email, subject, html_body, plain_text)

    return jsonify({'success': True, 'message': 'OTP sent'})

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM otps WHERE email=%s AND used=FALSE ORDER BY created_at DESC LIMIT 1", (email,))
        record = cursor.fetchone()

        if not record:
            return jsonify({'success': False, 'message': 'No pending OTP found'})

        if record['expires_at'] < datetime.now():
            return jsonify({'success': False, 'message': 'OTP expired'})

        if record['otp'] == otp:
            cursor.execute("UPDATE otps SET used=TRUE WHERE id=%s", (record['id'],))
            conn.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Invalid OTP'})
            
    except Exception as e:
        print(f"DB Error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == '__main__':
    app.run(port=5000, debug=True)
