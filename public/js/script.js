/* ==========================================================================
   OFFICIAL ENTERPRISE BANK MANAGEMENT SYSTEM - PORTAL CORE LOGIC
   ========================================================================== */

// Removed initDatabase

// Application & Navigation State
let currentUser = null;
let currentOtpCode = '';
let pendingOtpAction = null; // 'LOGIN', 'REGISTER', 'RESET_PASSWORD'
let pendingPayload = null;
let otpTimerInterval = null;
let otpTimeLeft = 120; // 2 minutes
let viewHistory = ['login']; // Navigation history stack for Back button

const captchas = {
    login: '',
    reg: '',
    reset: ''
};

// DOM Content Loaded Handler
document.addEventListener('DOMContentLoaded', () => {
    setupOtpBoxNavigation();
    checkExistingSession();
    startPortalClock();
    
    // Generate initial CAPTCHA challenges
    generateCaptcha('login');
    generateCaptcha('reg');
    generateCaptcha('reset');

});

/* ==========================================================================
   1. LIVE PORTAL CLOCK
   ========================================================================== */
function startPortalClock() {
    const clockEl = document.getElementById('portal-clock');
    if (!clockEl) return;
    const update = () => {
        const now = new Date();
        clockEl.textContent = now.toLocaleString('en-US', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        }) + ' IST';
    };
    update();
    setInterval(update, 1000);
}

/* ==========================================================================
   2. INTERACTIVE CAPTCHA GENERATOR (CANVAS BASED)
   ========================================================================== */
function generateCaptcha(type) {
    const canvas = document.getElementById(`${type}-captcha-canvas`);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let code = '';
    for (let i = 0; i < 5; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    captchas[type] = code;

    ctx.fillStyle = '#e2e8f0';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (let i = 0; i < 6; i++) {
        ctx.strokeStyle = `rgba(15, 23, 42, ${0.15 + Math.random() * 0.25})`;
        ctx.beginPath();
        ctx.moveTo(Math.random() * canvas.width, Math.random() * canvas.height);
        ctx.lineTo(Math.random() * canvas.width, Math.random() * canvas.height);
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    ctx.font = 'bold 22px "Roboto Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const charWidth = canvas.width / 5;
    for (let i = 0; i < code.length; i++) {
        ctx.save();
        const x = charWidth * i + charWidth / 2;
        const y = canvas.height / 2 + (Math.random() * 4 - 2);
        const angle = (Math.random() * 0.4) - 0.2;

        ctx.translate(x, y);
        ctx.rotate(angle);
        ctx.fillStyle = i % 2 === 0 ? '#1d4ed8' : '#0f172a';
        ctx.fillText(code[i], 0, 0);
        ctx.restore();
    }

    for (let i = 0; i < 30; i++) {
        ctx.fillStyle = `rgba(15, 23, 42, ${Math.random() * 0.3})`;
        ctx.beginPath();
        ctx.arc(Math.random() * canvas.width, Math.random() * canvas.height, 1, 0, Math.PI * 2);
        ctx.fill();
    }

    const inputField = document.getElementById(`${type}-captcha-input`);
    if (inputField) inputField.value = '';
}

function validateCaptcha(type) {
    const input = document.getElementById(`${type}-captcha-input`).value.trim().toUpperCase();
    const expected = captchas[type].toUpperCase();
    return input === expected;
}

/* ==========================================================================
   3. VIEW NAVIGATION & BACK BUTTON HISTORY
   ========================================================================== */
function switchView(viewName) {
    if (viewHistory[viewHistory.length - 1] !== viewName) {
        viewHistory.push(viewName);
    }
    
    // Purge Registration State on View Switching
    if (viewName === 'login' || viewName === 'register') {
        const loginForm = document.getElementById('login-form');
        if (loginForm) loginForm.reset();
        
        const registerForm = document.getElementById('register-form');
        if (registerForm) registerForm.reset();
        
        const regError = document.getElementById('reg-error-msg');
        if (regError) {
            regError.style.display = 'none';
            regError.textContent = '';
        }
        
        const loginError = document.getElementById('login-error-msg');
        if (loginError) {
            loginError.style.display = 'none';
            loginError.textContent = '';
        }
        
        // Clear password strength indicator
        if (typeof checkPasswordStrength === 'function') {
            checkPasswordStrength('');
        }
    }

    renderView(viewName);
}

function goBack() {
    if (viewHistory.length > 1) {
        viewHistory.pop(); // Remove current view
        const previousView = viewHistory[viewHistory.length - 1] || 'login';
        renderView(previousView);
    } else {
        renderView('login');
    }
}

function renderView(viewName) {
    const views = ['login-view', 'register-view', 'forgot-password-view', 'dashboard-view'];
    views.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.add('hidden');
            el.classList.remove('view-active');
        }
    });

    const targetView = document.getElementById(`${viewName}-view`);
    if (targetView) {
        targetView.classList.remove('hidden');
        targetView.classList.add('view-active');
    }

    if (viewName === 'forgot-password') {
        document.getElementById('forgot-password-form-1').classList.remove('hidden');
        document.getElementById('forgot-password-form-2').classList.add('hidden');
    }

    if (viewName === 'login') generateCaptcha('login');
    if (viewName === 'register') generateCaptcha('reg');
    if (viewName === 'forgot-password') generateCaptcha('reset');
}

/* ==========================================================================
   4. PASSWORD UTILITIES
   ========================================================================== */
function togglePasswordVisibility(inputId, btnEl) {
    const input = document.getElementById(inputId);
    const eyeOpen = btnEl.querySelector('.eye-open');
    const eyeClosed = btnEl.querySelector('.eye-closed');
    
    if (input.type === 'password') {
        input.type = 'text';
        eyeOpen.classList.add('hidden');
        eyeClosed.classList.remove('hidden');
    } else {
        input.type = 'password';
        eyeOpen.classList.remove('hidden');
        eyeClosed.classList.add('hidden');
    }
}

function checkPasswordStrength(val) {
    const bar = document.getElementById('strength-bar');
    const text = document.getElementById('strength-text');
    let score = 0;

    if (!val) {
        bar.style.width = '0%';
        bar.style.backgroundColor = 'transparent';
        text.textContent = 'Password Rating';
        text.style.color = ''; // Reset the color back to CSS default
        return;
    }

    if (val.length >= 6) score += 25;
    if (val.length >= 10) score += 25;
    if (/[A-Z]/.test(val)) score += 25;
    if (/[0-9!@#$%^&*]/.test(val)) score += 25;

    bar.style.width = `${score}%`;

    if (score <= 25) {
        bar.style.backgroundColor = '#dc2626';
        text.textContent = 'Weak Password';
        text.style.color = '#dc2626';
    } else if (score <= 50) {
        bar.style.backgroundColor = '#d97706';
        text.textContent = 'Moderate Password';
        text.style.color = '#d97706';
    } else if (score <= 75) {
        bar.style.backgroundColor = '#2563eb';
        text.textContent = 'Strong Password';
        text.style.color = '#2563eb';
    } else {
        bar.style.backgroundColor = '#059669';
        text.textContent = 'Bank-Grade Strong Password';
        text.style.color = '#059669';
    }
}

/* ==========================================================================
   5. AUTHENTICATION FORM HANDLERS (WITH CAPTCHA CHECK)
   ========================================================================== */

// 1. LOGIN HANDLER
async function handleLoginSubmit(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    if (!validateCaptcha('login')) {
        showToast('Invalid Security CAPTCHA code. Please re-enter the code.', 'error');
        generateCaptcha('login');
        return;
    }

    const btn = document.getElementById('btn-login');
    const errorMsgDiv = document.getElementById('login-error-msg');
    
    // Clear previous errors
    errorMsgDiv.style.display = 'none';
    errorMsgDiv.textContent = '';
    
    setButtonLoading(btn, true);

    try {
        const response = await fetch('http://localhost:5000/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        
        setButtonLoading(btn, false);

        if (!data.success) {
            // Always show inline error message
            errorMsgDiv.textContent = data.message;
            errorMsgDiv.style.display = 'block';

            if (response.status === 423 && data.lockout && data.remaining_seconds) {
                // --- HTTP 423: ACCOUNT LOCKED ---
                let timeLeft = data.remaining_seconds;
                const loginUser = document.getElementById('login-username');
                const loginPass = document.getElementById('login-password');
                const loginCap = document.getElementById('login-captcha-input');

                // Immediately clear ALL input fields (username, password, captcha)
                loginUser.value = '';
                loginPass.value = '';
                loginCap.value = '';

                // Disable all inputs and the login button
                btn.disabled = true;
                loginUser.disabled = true;
                loginPass.disabled = true;
                loginCap.disabled = true;

                // Re-clear after disable inside rAF to defeat any browser autofill
                // that may fire asynchronously after the initial .value = '' call
                requestAnimationFrame(() => {
                    loginUser.value = '';
                    loginPass.value = '';
                    loginCap.value = '';
                });

                // Real-time countdown: update every 1s
                const lockoutInterval = setInterval(() => {
                    timeLeft--;
                    errorMsgDiv.textContent = `Account locked. Please wait ${timeLeft}s...`;

                    if (timeLeft <= 0) {
                        clearInterval(lockoutInterval);

                        // Clear the error banner
                        errorMsgDiv.style.display = 'none';
                        errorMsgDiv.textContent = '';

                        // Re-enable all inputs and button
                        btn.disabled = false;
                        loginUser.disabled = false;
                        loginPass.disabled = false;
                        loginCap.disabled = false;

                        // Auto-refresh CAPTCHA for a clean retry
                        generateCaptcha('login');
                    }
                }, 1000);

            } else {
                // --- HTTP 401: INCORRECT CREDENTIALS ---
                // Keep username intact, clear password + captcha, refresh CAPTCHA
                const loginPass = document.getElementById('login-password');
                const loginCap = document.getElementById('login-captcha-input');
                loginPass.value = '';
                loginCap.value = '';
                generateCaptcha('login');
            }
            return;
        }

        // Pass email to triggerOtpFlow so the user gets the OTP
        triggerOtpFlow('LOGIN', data.email, { user: data.user });
    } catch (err) {
        setButtonLoading(btn, false);
        showToast('Cannot connect to server', 'error');
    }
}

// 2. REGISTER HANDLER
async function handleRegisterSubmit(e) {
    e.preventDefault();
    const firstName = document.getElementById('reg-firstname').value.trim();
    const lastName = document.getElementById('reg-lastname').value.trim();
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;

    if (!validateCaptcha('reg')) {
        showToast('Invalid Security CAPTCHA code. Please re-enter.', 'error');
        generateCaptcha('reg');
        return;
    }

    if (password.length < 6) {
        showToast('Password must be at least 6 characters long', 'error');
        return;
    }

    const btn = document.getElementById('btn-register');
    const errorMsgDiv = document.getElementById('reg-error-msg');
    
    // Clear previous errors
    if (errorMsgDiv) {
        errorMsgDiv.style.display = 'none';
        errorMsgDiv.textContent = '';
    }

    setButtonLoading(btn, true);

    try {
        setButtonLoading(btn, false);
        const payload = { username, email, password, firstName, lastName };
        triggerOtpFlow('REGISTER', email, payload);
    } catch (err) {
        setButtonLoading(btn, false);
        showToast('Cannot connect to server', 'error');
    }
}

// 3. FORGOT PASSWORD STEP 1 HANDLER
function handleForgotPasswordRequest(e) {
    e.preventDefault();
    const email = document.getElementById('reset-email').value.trim();

    if (!validateCaptcha('reset')) {
        showToast('Invalid Security CAPTCHA code. Please re-enter.', 'error');
        generateCaptcha('reset');
        return;
    }

    const btn = document.getElementById('btn-forgot-1');
    setButtonLoading(btn, true);

    setTimeout(() => {
        setButtonLoading(btn, false);
        triggerOtpFlow('RESET_PASSWORD', email, { userEmail: email });
    }, 500);
}

// 4. FORGOT PASSWORD STEP 2 HANDLER
async function handleNewPasswordSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('reset-verified-email').textContent;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-new-password').value;

    if (newPassword !== confirmPassword) {
        showToast('Passwords do not match', 'error');
        return;
    }

    if (newPassword.length < 6) {
        showToast('Password must be at least 6 characters', 'error');
        return;
    }

    const btn = document.getElementById('btn-forgot-2');
    setButtonLoading(btn, true);

    try {
        const response = await fetch('http://localhost:5000/api/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email: email, password: newPassword })
        });
        
        const data = await response.json();
        setButtonLoading(btn, false);

        // Helper refs for the two password fields and inline error div
        const newPwField = document.getElementById('new-password');
        const confirmPwField = document.getElementById('confirm-new-password');
        const resetErrDiv = document.getElementById('reset-pw-error-msg');

        if (!response.ok || !data.success) {
            if (response.status === 400 && data.error === 'same_password') {
                // Show inline red error directly below Confirm New Password
                resetErrDiv.textContent = data.message;
                resetErrDiv.style.display = 'block';
                // Immediately clear both password fields for a fresh re-entry
                newPwField.value = '';
                confirmPwField.value = '';
                newPwField.focus();
            } else {
                // Generic errors go to toast
                resetErrDiv.style.display = 'none';
                showToast(data.message || 'Password reset failed', 'error');
            }
            return;
        }

        // Clear any residual inline error on success
        resetErrDiv.style.display = 'none';
        resetErrDiv.textContent = '';

        document.getElementById('new-password').value = '';
        document.getElementById('confirm-new-password').value = '';
        document.getElementById('reset-email').value = '';
        document.getElementById('reset-verified-email').textContent = '';
        
        const resetForm2 = document.getElementById('forgot-password-form-2');
        if (resetForm2) resetForm2.reset();
        
        showToast('Password updated successfully! Please login.', 'success');
        switchView('login');
        
        document.getElementById('login-username').value = '';
        document.getElementById('login-password').value = '';
        const loginForm = document.getElementById('login-form');
        if (loginForm) loginForm.reset();
        
    } catch (err) {
        console.error('Password reset error:', err);
        setButtonLoading(btn, false);
        showToast('Cannot connect to server. Please try again later.', 'error');
    }
}

/* ==========================================================================
   6. REAL GMAIL OTP DISPATCH ENGINE
   ========================================================================== */

async function triggerOtpFlow(action, email, payload) {
    pendingOtpAction = action;
    pendingPayload = payload;
    
    document.getElementById('otp-target-display').textContent = email;

    const boxes = document.querySelectorAll('.otp-box');
    boxes.forEach(box => box.value = '');
    boxes[0].focus();

    document.getElementById('otp-modal-overlay').classList.remove('hidden');

    startOtpTimer();

    await sendRealOtpEmail(email, action);
}

async function sendRealOtpEmail(targetEmail, action) {
    try {
        const bodyData = { email: targetEmail, action: action };
        if (action === 'REGISTER' && typeof pendingPayload !== 'undefined' && pendingPayload && pendingPayload.username) {
            bodyData.username = pendingPayload.username;
        }
        
        const response = await fetch('http://localhost:5000/api/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bodyData)
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            closeOtpModal();
            showToast(data.message || 'Failed to send OTP', 'error');
        }
    } catch (e) {
        closeOtpModal();
        showToast('Backend server unreachable. Cannot send OTP.', 'error');
        console.error('OTP Send error:', e);
    }
}

function closeOtpModal() {
    document.getElementById('otp-modal-overlay').classList.add('hidden');
    if (otpTimerInterval) clearInterval(otpTimerInterval);
}

function startOtpTimer() {
    if (otpTimerInterval) clearInterval(otpTimerInterval);
    otpTimeLeft = 300;
    const timerDisplay = document.getElementById('otp-countdown');
    const resendBtn = document.getElementById('resend-otp-btn');
    resendBtn.disabled = true;

    otpTimerInterval = setInterval(() => {
        otpTimeLeft--;
        const mins = Math.floor(otpTimeLeft / 60).toString().padStart(2, '0');
        const secs = (otpTimeLeft % 60).toString().padStart(2, '0');
        timerDisplay.textContent = `${mins}:${secs}`;

        if (otpTimeLeft <= 0) {
            clearInterval(otpTimerInterval);
            timerDisplay.textContent = '00:00';
            resendBtn.disabled = false;
            showToast('OTP expired. Click Resend Gmail OTP.', 'error');
        }
    }, 1000);
}

async function resendOtpCode() {
    const targetEmail = document.getElementById('otp-target-display').textContent;
    startOtpTimer();
    const boxes = document.querySelectorAll('.otp-box');
    boxes.forEach(box => box.value = '');
    boxes[0].focus();

    await sendRealOtpEmail(targetEmail, pendingOtpAction);
}

function setupOtpBoxNavigation() {
    const boxes = document.querySelectorAll('.otp-box');
    boxes.forEach((box, idx) => {
        box.addEventListener('input', (e) => {
            const val = e.target.value;
            if (val.length === 1 && idx < boxes.length - 1) {
                boxes[idx + 1].focus();
            }
            
            let fullCode = '';
            boxes.forEach(b => fullCode += b.value);
            if (fullCode.length === 6) {
                submitOtpVerification();
            }
        });

        box.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !box.value && idx > 0) {
                boxes[idx - 1].focus();
            }
        });

        box.addEventListener('paste', (e) => {
            e.preventDefault();
            const pasteData = (e.clipboardData || window.clipboardData).getData('text').trim();
            if (/^\d{6}$/.test(pasteData)) {
                for (let i = 0; i < Math.min(pasteData.length, boxes.length); i++) {
                    boxes[i].value = pasteData[i];
                }
                submitOtpVerification();
            }
        });
    });
}

async function submitOtpVerification() {
    const boxes = document.querySelectorAll('.otp-box');
    let enteredCode = '';
    boxes.forEach(b => enteredCode += b.value);

    if (enteredCode.length < 6) {
        showToast('Please enter the full 6-digit OTP code', 'error');
        return;
    }

    const btn = document.getElementById('btn-verify-otp');
    setButtonLoading(btn, true);
    
    const targetEmail = document.getElementById('otp-target-display').textContent;

    try {
        const response = await fetch('http://localhost:5000/api/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email: targetEmail, otp: enteredCode, action: pendingOtpAction })
        });
        const data = await response.json();
        
        setButtonLoading(btn, false);

        if (!data.success) {
            showToast('Invalid OTP Code. Please check your Gmail inbox.', 'error');
            return;
        }

        closeOtpModal();

        if (pendingOtpAction === 'LOGIN') {
            completeLogin(pendingPayload.user);
        } else if (pendingOtpAction === 'REGISTER') {
            try {
                const regResponse = await fetch('http://localhost:5000/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(pendingPayload)
                });
                const regData = await regResponse.json();
                
                if (regData.success) {
                    showToast('Registration successful! Please log in.', 'success');
                    const regForm = document.getElementById('register-form');
                    if (regForm) regForm.reset();
                    ['reg-firstname', 'reg-lastname', 'reg-email', 'reg-username', 'reg-password', 'reg-captcha-input'].forEach(id => {
                        const el = document.getElementById(id);
                        if (el) el.value = '';
                    });
                    if (typeof checkPasswordStrength === 'function') checkPasswordStrength('');
                    switchView('login');
                } else {
                    showToast(regData.message || 'Registration failed', 'error');
                }
            } catch (e) {
                showToast('Registration server error', 'error');
            }
        } else if (pendingOtpAction === 'RESET_PASSWORD') {
            document.getElementById('reset-verified-email').textContent = pendingPayload.userEmail;
            document.getElementById('forgot-password-form-1').classList.add('hidden');
            document.getElementById('forgot-password-form-2').classList.remove('hidden');

            // Auto-dismiss the OTP verified banner after 3.5 seconds
            const otpBanner = document.querySelector('#forgot-password-form-2 .step-indicator');
            if (otpBanner) {
                setTimeout(() => {
                    otpBanner.classList.add('fade-out');
                    // Remove from layout after transition completes (400ms)
                    setTimeout(() => { otpBanner.style.display = 'none'; }, 420);
                }, 3500);
            }
        }

    } catch (err) {
        setButtonLoading(btn, false);
        showToast('Cannot connect to server', 'error');
    }
}

/* ==========================================================================
   7. SESSION & DASHBOARD MANAGEMENT
   ========================================================================== */

function completeLogin(user) {
    currentUser = user;
    sessionStorage.setItem('bank_active_session', JSON.stringify(user));
    
    document.getElementById('dash-user-name').textContent = user.name;
    document.getElementById('dash-acc-num').textContent = `ACC: ${user.accountNumber}`;
    document.getElementById('dash-acc-type').textContent = user.accountType || 'Premier Vault Account';
    document.getElementById('dash-balance').textContent = user.balance || '148,920.50';
    
    const initials = user.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
    document.getElementById('dash-avatar').textContent = initials || 'JD';

    document.getElementById('last-login-time').textContent = `Just Now • ${new Date().toLocaleTimeString()} (Gmail OTP Verified)`;

    window.location.href = '/home/landingPage/homePage';
}

function checkExistingSession() {
    const sessionStr = sessionStorage.getItem('bank_active_session');
    if (!sessionStr) return;

    const onOverviewPage = window.location.pathname.startsWith('/home/landingPage/');

    try {
        const user = JSON.parse(sessionStr);
        if (onOverviewPage) {
            // Already on dashboard — just populate the DOM, do NOT redirect.
            currentUser = user;
            const nameEl = document.getElementById('dash-user-name');
            const accEl  = document.getElementById('dash-acc-num');
            const typeEl = document.getElementById('dash-acc-type');
            const balEl  = document.getElementById('dash-balance');
            const avEl   = document.getElementById('dash-avatar');
            const tsEl   = document.getElementById('last-login-time');
            if (nameEl) nameEl.textContent = user.name;
            if (accEl)  accEl.textContent  = `ACC: ${user.accountNumber}`;
            if (typeEl) typeEl.textContent  = user.accountType || 'Premier Vault Account';
            if (balEl)  balEl.textContent   = user.balance || '148,920.50';
            if (avEl) {
                const initials = user.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
                avEl.textContent = initials || 'JD';
            }
            if (tsEl) tsEl.textContent = `Last Session • (Gmail OTP Verified)`;
        } else {
            // On the login SPA — redirect to dashboard since session is valid.
            window.location.href = '/home/landingPage/homePage';
        }
    } catch(e) {
        sessionStorage.removeItem('bank_active_session');
    }
}

function handleLogout() {
    sessionStorage.removeItem('bank_active_session');
    currentUser = null;
    // Navigate to server-side logout route which clears any server session
    // and redirects to /registration/welcome.
    window.location.href = '/logout';
}

function triggerQuickAction(actionName) {
    if (actionName === 'Overview') {
        window.location.href = '/home/landingPage/homePage';
        return;
    }
    if (actionName === 'Accounts dashboard' || actionName === 'Accounts') {
        window.location.href = '/home/landingPage/manageRelationship/transactionAccounts';
        return;
    }
    showTimeoutModal("This feature is currently under development.");
}

function showHelpModal(e) {
    e.preventDefault();
    showToast('Customer Help Desk: Call Toll Free 1-800-555-BANK or email support@bankportal.com', 'info');
}

/* ==========================================================================
   INTERACTIVE SPX BANK PLUGINS
   ========================================================================== */
function playCaptchaSound(type) {
    if ('speechSynthesis' in window) {
        const code = captchas[type];
        if (code) {
            const utterance = new SpeechSynthesisUtterance(code.split('').join(' '));
            utterance.rate = 0.75;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
            showToast('Reading CAPTCHA aloud...', 'success');
        }
    } else {
        showToast('Text-to-speech is not supported in your browser.', 'error');
    }
}

function toggleBalanceVisibility() {
    const balanceEl = document.getElementById('dash-balance');
    const eyeIcon = document.getElementById('balance-eye-icon');
    if (!balanceEl || !eyeIcon) return;

    const isHidden = balanceEl.getAttribute('data-hidden') === 'true';
    if (isHidden) {
        // Show balance
        balanceEl.textContent = currentUser ? currentUser.balance : '148,920.50';
        balanceEl.setAttribute('data-hidden', 'false');
        eyeIcon.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
        showToast('Balance shown', 'info');
    } else {
        // Hide balance
        balanceEl.textContent = 'XXXX.XX';
        balanceEl.setAttribute('data-hidden', 'true');
        eyeIcon.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;
        showToast('Balance hidden', 'info');
    }
}

function showTimeoutModal(message) {
    const modal = document.getElementById('timeout-modal-overlay');
    const textEl = document.getElementById('timeout-message-text');
    if (modal) {
        if (textEl && message) {
            textEl.textContent = message;
        }
        modal.classList.remove('hidden');
    }
}

function closeTimeoutModal() {
    const modal = document.getElementById('timeout-modal-overlay');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/* ==========================================================================
   8. UI UTILITIES (TOASTS & SPINNERS)
   ========================================================================== */

function getUsersFromStorage() {
    return [];
}

function setButtonLoading(button, isLoading) {
    const textEl = button.querySelector('.btn-text');
    const spinnerEl = button.querySelector('.btn-spinner');
    const arrowEl = button.querySelector('.btn-arrow');

    if (isLoading) {
        button.disabled = true;
        if (textEl) textEl.style.opacity = '0.5';
        if (spinnerEl) spinnerEl.classList.remove('hidden');
        if (arrowEl) arrowEl.classList.add('hidden');
    } else {
        button.disabled = false;
        if (textEl) textEl.style.opacity = '1';
        if (spinnerEl) spinnerEl.classList.add('hidden');
        if (arrowEl) arrowEl.classList.remove('hidden');
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let iconSvg = '';
    if (type === 'success') {
        iconSvg = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#059669" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
    } else if (type === 'error') {
        iconSvg = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#dc2626" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
    } else {
        iconSvg = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#1d4ed8" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `${iconSvg} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}
let previouslyActiveTab = null;

document.addEventListener('DOMContentLoaded', () => {
  const paymentsBtn    = document.getElementById('nav-payments-tab');
  const depositsBtn    = document.getElementById('nav-deposits-tab');
  const megaMenu       = document.querySelector('.spx-mega-menu');
  const depositsMegaMenu = document.querySelector('.spx-deposits-mega-menu');
  const overlay        = document.getElementById('mega-menu-overlay');

  // ── Helper: close ALL mega-menus and restore previously-active tab ──
  function closeAllMenus(restoreTab) {
    if (megaMenu)        { megaMenu.classList.remove('active'); }
    if (depositsMegaMenu){ depositsMegaMenu.classList.remove('active'); }
    if (paymentsBtn)     { paymentsBtn.classList.remove('mega-active'); }
    if (depositsBtn)     { depositsBtn.classList.remove('mega-active'); }
    if (overlay)         { overlay.classList.remove('active'); }
    if (restoreTab && previouslyActiveTab) {
      previouslyActiveTab.classList.add('active');
      previouslyActiveTab = null;
    }
  }

  // ── Helper: open a specific menu, centred under its trigger button ──
  function openMenu(menu, triggerBtn) {
    if (!menu || !triggerBtn) return;
    const tabRect    = triggerBtn.getBoundingClientRect();
    const parentRect = menu.offsetParent
        ? menu.offsetParent.getBoundingClientRect()
        : { left: 0 };
    const tabCentre  = tabRect.left + tabRect.width / 2 - parentRect.left;
    const menuHalf   = menu.offsetWidth / 2 || 270; // fallback 270 = 540/2
    menu.style.left      = (tabCentre - menuHalf) + 'px';
    menu.style.transform = 'none';
    menu.classList.add('active');
    triggerBtn.classList.add('mega-active');
    if (overlay) overlay.classList.add('active');
  }

  // ── Payments tab ──
  if (paymentsBtn && megaMenu) {
    paymentsBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const isOpening = !megaMenu.classList.contains('active');
      if (isOpening) {
        // Snapshot active tab before closing it
        const activeTab = document.querySelector('.spx-nav-item.active');
        if (activeTab && activeTab !== paymentsBtn) {
          previouslyActiveTab = activeTab;
          activeTab.classList.remove('active');
        }
        closeAllMenus(false);   // close Deposits (if open) without restoring
        openMenu(megaMenu, paymentsBtn);
      } else {
        closeAllMenus(true);
      }
    });
  }

  // ── Deposits tab ──
  if (depositsBtn && depositsMegaMenu) {
    depositsBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const isOpening = !depositsMegaMenu.classList.contains('active');
      if (isOpening) {
        // Snapshot active tab before closing it
        const activeTab = document.querySelector('.spx-nav-item.active');
        if (activeTab && activeTab !== depositsBtn) {
          previouslyActiveTab = activeTab;
          activeTab.classList.remove('active');
        }
        closeAllMenus(false);   // close Payments (if open) without restoring
        openMenu(depositsMegaMenu, depositsBtn);
      } else {
        closeAllMenus(true);
      }
    });
  }

  // ── Outside-click / overlay-click: close everything ──
  document.addEventListener('click', (e) => {
    const clickedInsidePayments = paymentsBtn && paymentsBtn.contains(e.target);
    const clickedInsideDeposits = depositsBtn && depositsBtn.contains(e.target);
    const clickedInPaymentsMenu = megaMenu && megaMenu.contains(e.target);
    const clickedInDepositsMenu = depositsMegaMenu && depositsMegaMenu.contains(e.target);

    if (!clickedInsidePayments && !clickedInsideDeposits &&
        !clickedInPaymentsMenu && !clickedInDepositsMenu) {
      closeAllMenus(true);
    }
  });
});

