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
    body_desc = "Use the OTP below to complete your sign-in. This code is valid for 5 minutes."
    security_note = "🔒 Never share this OTP with anyone, including SPX Bank staff."
    footer_text = "If you didn't request this code, you can safely ignore this email."

    if action == 'REGISTER':
        subject = "Verify your email to complete SPX Bank registration"
        heading = "Verify your email address"
        body_desc = "Use the OTP below to verify your email and complete your SPX Bank account registration. This code is valid for 5 minutes."
        security_note = "🔒 Never share this OTP with anyone, including SPX Bank staff."
        footer_text = "If you didn't attempt to create an account with SPX Bank, please ignore this email."
    elif action == 'RESET_PASSWORD':
        subject = "Reset your SPX Bank account password"
        heading = "Reset your SPX Bank password"
        body_desc = "We received a request to reset your netbanking password. Use the code below to proceed. Valid for 5 minutes."
        security_note = "🔒 SPX Bank will never ask for this code. Do not share it with anyone."
        footer_text = "If you didn't request a password reset, please ignore this email or secure your account."

    plain_text = f"{heading}\n\n{body_desc}\n\nVerification Code: {otp}\n\n{security_note}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f8f9fa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <span style="display:none; font-size:1px; color:#ffffff; line-height:1px; max-height:0px; max-width:0px; opacity:0; overflow:hidden;">
            Your SPX Bank verification code is enclosed. Please do not share this code with anyone.
        </span>
        <div style="background-color: #f8f9fa; padding: 40px 20px;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); padding: 40px; border: 1px solid #eaeaea;">
                <h1 style="color: #111827; font-size: 20px; font-weight: 700; margin-top: 0; margin-bottom: 16px; text-align: center;">
                    {heading}
                </h1>
                
                <p style="color: #4b5563; font-size: 15px; line-height: 1.6; margin-bottom: 30px; text-align: center;">
                    {body_desc}
                </p>
                
                <div style="background-color: #f4f5f7; border: 1px solid #eaeaea; padding: 24px; text-align: center; border-radius: 6px; margin-bottom: 30px;">
                    <div style="font-size: 32px; font-weight: 700; color: #5C2D91; letter-spacing: 6px; margin-left: 8px;">
                        {otp}
                    </div>
                </div>
                
                <p style="color: #6b7280; font-size: 13px; line-height: 1.5; margin-bottom: 0; text-align: center;">
                    {security_note}
                </p>
                
                <hr style="border: none; border-top: 1px solid #eaeaea; margin: 30px 0;">
                
                <div style="text-align: center; color: #9ca3af; font-size: 12px; line-height: 1.5;">
                    <p style="margin: 0 0 8px 0;">{footer_text}</p>
                    <p style="margin: 0;">&copy; 2026 SPX Bank. All rights reserved.</p>
                    <p style="font-size: 11px; color: #888888; margin-top: 15px;">
                        <span style="display:none; font-size:1px; color:#ffffff; opacity:0;">Ref: {uuid.uuid4()}</span>
                    </p>
                </div>
            </div>
        </div>
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

        # Logo attachment logic removed

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
        
        if action == 'RESET_PASSWORD' and not user_record:
            return jsonify({'success': False, 'message': 'No account found with this email address'}), 404

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

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    new_password = data.get('password')

    if not email or not new_password:
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

    try:
        conn = get_db_connection()

        # Use a buffered cursor (or close after fetch) to avoid "Unread result found"
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(
            "SELECT id FROM otps WHERE email=%s AND used=TRUE AND created_at >= NOW() - INTERVAL 15 MINUTE",
            (email,)
        )
        otp_row = cursor.fetchone()
        cursor.close()

        if not otp_row:
            return jsonify({'success': False, 'message': 'No verified OTP found for this email. Please request a new OTP.'}), 403

        # Use a fresh cursor for the UPDATE 
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash=%s WHERE email=%s", (hashed_pw, email))
        conn.commit()

        affected = cursor.rowcount
        print(f"Reset password request for {email}, affected rows: {affected}")

        cursor.close()

        if affected == 0:
            return jsonify({'success': False, 'message': 'No account found with this email address or update failed'}), 404

        return jsonify({'success': True, 'message': 'Password reset successful'})
    except Exception as e:
        print(f"DB Error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    app.run(port=5000, debug=True)
