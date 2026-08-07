import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, g, make_response
from flask_cors import CORS
import mysql.connector
import bcrypt
import random
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uuid
import jwt
from functools import wraps

load_dotenv()

app = Flask(__name__, static_folder='public', static_url_path='/public')
app.secret_key = os.environ.get('SECRET_KEY', 'default-dev-key-change-in-prod')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
CORS(app, supports_credentials=True)

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'database': os.environ.get('DB_NAME', 'spxbank')
}

db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="spxbank_pool",
    pool_size=5,
    pool_reset_session=True,
    **DB_CONFIG
)

def get_db_connection():
    return db_pool.get_connection()

def run_migrations():
    """Auto-migrate DB schema on startup. Safe to run repeatedly."""
    migrations = [
        # Add action column to otps if it doesn't already exist
        "ALTER TABLE otps ADD COLUMN action VARCHAR(50) NOT NULL DEFAULT 'LOGIN'",
    ]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        for sql in migrations:
            try:
                cursor.execute(sql)
                conn.commit()
                print(f"[MIGRATION OK] {sql[:60]}...")
            except Exception as e:
                # 1060 = Duplicate column name — column already exists, safe to skip
                if hasattr(e, 'errno') and e.errno == 1060:
                    print(f"[MIGRATION SKIP] Column already exists — {sql[:60]}")
                else:
                    print(f"[MIGRATION WARN] {e}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[MIGRATION ERROR] Could not connect for migrations: {e}")

run_migrations()

# ==========================================================================
# JWT HELPERS
# ==========================================================================
JWT_SECRET = os.environ.get('SECRET_KEY', 'default-dev-key-change-in-prod')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_MINUTES = 15

def generate_jwt_token(user_id, username):
    """Generate a short-lived JWT bearing user_id and username."""
    payload = {
        'sub': str(user_id),
        'username': username,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(minutes=JWT_EXPIRY_MINUTES)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def token_required(f):
    """Decorator: extract + verify Bearer JWT from Authorization header or cookie.
    - API callers (Accept: application/json) receive JSON 401.
    - Browser page visits (Accept: text/html) are redirected to / for re-login.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        is_browser = 'text/html' in request.headers.get('Accept', '')
        token = request.cookies.get('bank_jwt_token')
        if not token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ', 1)[1]
        if not token:
            token = request.args.get('token')
            
        def handle_unauthorized(msg):
            if is_browser:
                resp = redirect(url_for('index'))
                resp.delete_cookie('bank_jwt_token')
                return resp
            return jsonify({'success': False, 'message': msg}), 401

        if not token:
            return handle_unauthorized('Authorization token missing')
            
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            g.user = payload
        except jwt.ExpiredSignatureError:
            return handle_unauthorized('Token expired. Please log in again.')
        except jwt.InvalidTokenError:
            return handle_unauthorized('Invalid token.')
            
        return f(*args, **kwargs)
    return decorated
# ==========================================================================

def get_email_template(action, first_name, otp):
    subject = "Login Verification OTP"
    heading = "Verify your SPX Bank login"
    body_desc = "Use the OTP below to complete your sign-in. This code is valid for 5 minutes."
    security_note = "🔒 Never share this OTP with anyone, including SPX Bank staff."
    footer_text = "If you didn't request this code, you can safely ignore this email."

    if action == 'REGISTER':
        subject = "Registration Verification OTP"
        heading = "Verify your email address"
        body_desc = "Use the OTP below to verify your email and complete your SPX Bank account registration. This code is valid for 5 minutes."
        security_note = "🔒 Never share this OTP with anyone, including SPX Bank staff."
        footer_text = "If you didn't attempt to create an account with SPX Bank, please ignore this email."
    elif action == 'RESET_PASSWORD':
        subject = "Password Reset OTP"
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

# --- VIEW ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/overview')
@token_required
def overview_protected():
    """JWT-protected dashboard view. Redirects to / if token missing/invalid."""
    resp = make_response(render_template('overview.html'))
    # If a token was provided in the query string (JS fallback), set the HTTP-only cookie now.
    token_query = request.args.get('token')
    if token_query:
        resp.set_cookie('bank_jwt_token', token_query, httponly=True, samesite='Lax', max_age=900)
    return resp

@app.route('/home/landingPage/homePage')
def overview_legacy():
    """Legacy SBI-style URL kept for compatibility."""
    return render_template('overview.html')

@app.route('/home/landingPage/manageRelationship/transactionAccounts')
def accounts():
    return render_template('accounts.html')
# -------------------

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
        cursor = conn.cursor(dictionary=True)
        
        # 1. Enforce OTP validation
        cursor.execute("SELECT * FROM otps WHERE email=%s AND used=TRUE ORDER BY created_at DESC LIMIT 1", (email,))
        otp_record = cursor.fetchone()
        
        if not otp_record:
            return jsonify({'success': False, 'message': 'OTP verification required'}), 403
            
        if otp_record['expires_at'] < datetime.now():
            return jsonify({'success': False, 'message': 'Verified OTP has expired. Please request a new one.'}), 403

        # 2. Duplicate check
        cursor.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Username or email already exists'}), 409
            
        # 3. Consume OTP
        cursor.execute("DELETE FROM otps WHERE id=%s", (otp_record['id'],))
        
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
        # Registration complete — return redirect signal. No auto-login.
        return jsonify({'success': True, 'message': 'Registration successful', 'redirect': '/'})
        
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
        if user['lockout_until']:
            if user['lockout_until'] > now:
                remaining = int((user['lockout_until'] - now).total_seconds())
                print(f"[LOCKOUT BLOCKED] Login attempt rejected for locked user: {username}")
                return jsonify({'success': False, 'error': 'Account locked', 'lockout': True, 'remaining_seconds': remaining, 'message': f'Account locked. Please wait {remaining} seconds.'}), 423
            else:
                cursor.execute("UPDATE users SET failed_attempts=0, lockout_until=NULL WHERE id=%s", (user['id'],))
                conn.commit()
                user['failed_attempts'] = 0
                user['lockout_until'] = None
                print(f"[LOCKOUT EXPIRED] Resetting failed attempts and lockout timestamp for user: {username}")

        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # Reset attempts on success
            cursor.execute("UPDATE users SET failed_attempts=0, lockout_until=NULL WHERE id=%s", (user['id'],))
            conn.commit()

            # Issue JWT token
            token = generate_jwt_token(user['id'], user['username'])

            user_obj = {
                'username': user['username'],
                'name': f"{user['first_name']} {user['last_name']}",
                'email': user['email'],
                'accountType': 'Savings Account',
                'accountNumber': user['account_number'],
                'balance': str(user['balance'])
            }
            print(f"[LOGIN OK] JWT issued for user: {username}")
            resp = jsonify({
                'success': True,
                'token': token,
                'user': user_obj,
                'redirect': '/overview'
            })
            # Set JWT as HttpOnly cookie so browser page navigations carry auth automatically
            resp.set_cookie(
                'bank_jwt_token',
                token,
                httponly=True,
                samesite='Lax',
                max_age=900   # 15 minutes, matching JWT expiry
            )
            return resp
        else:
            # Failed attempt
            attempts = user['failed_attempts'] + 1
            if attempts >= 3:
                lockout_time = now + timedelta(seconds=30)
                cursor.execute("UPDATE users SET failed_attempts=%s, lockout_until=%s WHERE id=%s", (attempts, lockout_time, user['id']))
                conn.commit()
                return jsonify({'success': False, 'error': 'Account locked', 'lockout': True, 'remaining_seconds': 30, 'message': 'Account locked. Please wait 30 seconds.'}), 423
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

@app.route('/api/logout', methods=['POST'])
def logout():
    resp = jsonify({'success': True, 'message': 'Logged out'})
    resp.delete_cookie('bank_jwt_token', samesite='Lax')
    print(f"[LOGOUT] JWT cookie cleared")
    return resp

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
        
        if action == 'REGISTER':
            cursor.execute("SELECT id FROM users WHERE username=%s OR email=%s", (frontend_username, email))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Username or email already exists'}), 409
        
        if action == 'RESET_PASSWORD' and not user_record:
            return jsonify({'success': False, 'message': 'No account found with this email address'}), 404

        if user_record:
            if user_record.get('first_name'):
                first_name = user_record['first_name']
            elif user_record.get('username'):
                first_name = user_record['username']

        cursor.execute("INSERT INTO otps (email, otp, action, expires_at) VALUES (%s, %s, %s, %s)", (email, otp, action, expires_at))
        conn.commit()
    except Exception as e:
        print(f"[SEND-OTP ERROR] {e}")
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

            # For RESET_PASSWORD: store verified email in server-side session
            action = data.get('action', '')
            if action == 'RESET_PASSWORD':
                from flask import session as flask_session
                flask_session['verified_reset_email'] = email
                flask_session['verified_reset_at'] = datetime.now().isoformat()
                print(f"[RESET SESSION SET] verified_reset_email={email}")

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
    from flask import session as flask_session
    data = request.json
    email = data.get('email')
    new_password = data.get('password')

    if not email or not new_password:
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    # --- Auth check: Flask session (primary) OR DB-verified OTP fallback ---
    session_email = flask_session.get('verified_reset_email')
    is_session_verified = (session_email == email)

    if not is_session_verified:
        # Fallback: check otps table for a verified RESET_PASSWORD OTP within 15 min
        try:
            conn_check = get_db_connection()
            cursor_check = conn_check.cursor(dictionary=True, buffered=True)
            cursor_check.execute(
                "SELECT id FROM otps WHERE email=%s AND action='RESET_PASSWORD' AND used=TRUE AND created_at >= NOW() - INTERVAL 15 MINUTE ORDER BY created_at DESC LIMIT 1",
                (email,)
            )
            otp_fallback = cursor_check.fetchone()
            cursor_check.close()
            conn_check.close()
        except Exception as db_e:
            print(f"[RESET AUTH CHECK ERROR] {db_e}")
            otp_fallback = None

        if not otp_fallback:
            print(f"[RESET REJECTED] No valid session or verified OTP for {email}")
            return jsonify({'success': False, 'message': 'Session expired or unauthorized. Please restart the password reset flow.'}), 403

        print(f"[RESET AUTH] DB-fallback OTP verification passed for {email}")
    else:
        print(f"[RESET AUTH] Session verification passed for {email}")

    try:
        conn = get_db_connection()

        # Fetch the current password hash to check for reuse
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT password_hash FROM users WHERE email=%s", (email,))
        user_row = cursor.fetchone()
        cursor.close()

        if user_row and bcrypt.checkpw(new_password.encode('utf-8'), user_row['password_hash'].encode('utf-8')):
            return jsonify({'success': False, 'error': 'same_password', 'message': 'New password cannot be the same as the old password.'}), 400

        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash=%s WHERE email=%s", (hashed_pw, email))
        conn.commit()

        affected = cursor.rowcount
        print(f"[RESET SUCCESS] Password updated for {email}, rows affected: {affected}")
        cursor.close()

        if affected == 0:
            return jsonify({'success': False, 'message': 'No account found with this email address or update failed'}), 404

        # Clear the session flag — single use
        flask_session.pop('verified_reset_email', None)
        flask_session.pop('verified_reset_at', None)

        return jsonify({'success': True, 'message': 'Password reset successful'})
    except Exception as e:
        print(f"[RESET ERROR] {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    app.run(port=5000, debug=True)
