from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import sqlite3
import hashlib
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'feedback-secret-key-change-in-production'

DB = "feedback.db"

# ── Database ───────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'applicant',
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        email TEXT,
        rating INTEGER,
        category TEXT,
        message TEXT,
        recommend TEXT,
        submitted_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS loan_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        applicant_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        loan_amount REAL NOT NULL,
        loan_type TEXT NOT NULL,
        employment_status TEXT NOT NULL,
        employer_name TEXT,
        monthly_income REAL NOT NULL,
        credit_score INTEGER,
        collateral_type TEXT,
        collateral_value REAL,
        purpose TEXT,
        documents TEXT,
        status TEXT DEFAULT 'pending',
        appraisal_status TEXT DEFAULT 'not_started',
        appraiser_id INTEGER,
        appraiser_notes TEXT,
        validity_flag TEXT,
        ltv_ratio REAL,
        dti_ratio REAL,
        submitted_at TEXT NOT NULL,
        appraisal_started_at TEXT,
        appraisal_completed_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (appraiser_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS appraisal_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_application_id INTEGER NOT NULL,
        appraiser_id INTEGER NOT NULL,
        activity_type TEXT NOT NULL,
        description TEXT NOT NULL,
        performed_at TEXT NOT NULL,
        FOREIGN KEY (loan_application_id) REFERENCES loan_applications(id),
        FOREIGN KEY (appraiser_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS document_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_application_id INTEGER NOT NULL,
        appraiser_id INTEGER NOT NULL,
        document_type TEXT NOT NULL,
        request_message TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        requested_at TEXT NOT NULL,
        responded_at TEXT,
        FOREIGN KEY (loan_application_id) REFERENCES loan_applications(id),
        FOREIGN KEY (appraiser_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ── Auth Guard ─────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_page'))
        return f(*args, **kwargs)
    return decorated

def appraiser_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_page'))
        if session.get('user_role') != 'appraiser':
            return jsonify({'success': False, 'message': 'Unauthorized. Appraiser access only.'}), 403
        return f(*args, **kwargs)
    return decorated

# ── Page Routes ────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('form_page'))
    return redirect(url_for('auth_page'))

@app.route('/auth')
def auth_page():
    if 'user_id' in session:
        return redirect(url_for('form_page'))
    return render_template('auth.html')

@app.route('/form')
@login_required
def form_page():
    return render_template('index.html', user_name=session.get('user_name'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user_name=session.get('user_name'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth_page'))

# ── Loan Application Routes ────────────────────────────────────────────────
@app.route('/loan/apply')
@login_required
def loan_application_page():
    return render_template('loan_application.html', user_name=session.get('user_name'))

@app.route('/loan/my-applications')
@login_required
def my_applications():
    return render_template('my_applications.html', user_name=session.get('user_name'))

# ── Appraiser Routes ───────────────────────────────────────────────────────
@app.route('/appraiser/dashboard')
@login_required
def appraiser_dashboard():
    if session.get('user_role') != 'appraiser':
        return redirect(url_for('form_page'))
    return render_template('appraiser_dashboard.html', user_name=session.get('user_name'))

@app.route('/appraiser/application/<int:app_id>')
@login_required
def appraiser_application_detail(app_id):
    if session.get('user_role') != 'appraiser':
        return redirect(url_for('form_page'))
    return render_template('appraiser_detail.html', user_name=session.get('user_name'), app_id=app_id)

# ── Auth API ───────────────────────────────────────────────────────────────────

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm = data.get('confirm_password', '')
    role = data.get('role', 'applicant').strip()

    if not all([name, email, password, confirm]):
        return jsonify({'success': False, 'message': 'All fields are required.'})
    if password != confirm:
        return jsonify({'success': False, 'message': 'Passwords do not match.'})
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters.'})

    conn = get_db()
    existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'success': False, 'message': 'Email already registered. Please login.'})

    conn.execute('INSERT INTO users (name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)',
                 (name, email, hash_password(password), role, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['user_role'] = user['role']
    
    if role == 'appraiser':
        return jsonify({'success': True, 'redirect': '/appraiser/dashboard'})
    return jsonify({'success': True, 'redirect': '/form'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required.'})

    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?',
                        (email, hash_password(password))).fetchone()
    conn.close()

    if not user:
        return jsonify({'success': False, 'message': 'Invalid email or password.'})

    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['user_role'] = user['role']
    
    if user['role'] == 'appraiser':
        return jsonify({'success': True, 'redirect': '/appraiser/dashboard'})
    return jsonify({'success': True, 'redirect': '/form'})

# ── Feedback API ───────────────────────────────────────────────────────────────

@app.route('/api/submit', methods=['POST'])
@login_required
def submit():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided.'}), 400
        
        # Validate required fields
        rating = data.get('rating')
        category = data.get('category', '').strip()
        message = data.get('message', '').strip()
        recommend = data.get('recommend', '').strip()
        
        if not rating:
            return jsonify({'success': False, 'message': 'Please select a rating.'}), 400
        
        if not category:
            return jsonify({'success': False, 'message': 'Please select a category.'}), 400
        
        if not message:
            return jsonify({'success': False, 'message': 'Please enter a message.'}), 400
        
        if not recommend:
            return jsonify({'success': False, 'message': 'Please select an option for recommendation.'}), 400
        
        # Convert rating to int
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return jsonify({'success': False, 'message': 'Rating must be between 1 and 5.'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid rating value.'}), 400
        
        conn = get_db()
        conn.execute('''INSERT INTO feedback (user_id, name, email, rating, category, message, recommend, submitted_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (session['user_id'], session['user_name'], session['user_email'],
                      rating, category, message, recommend, 
                      datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Feedback submitted!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/results')
@login_required
def results():
    conn = get_db()
    rows = conn.execute('SELECT * FROM feedback ORDER BY submitted_at DESC').fetchall()
    total = len(rows)

    if total == 0:
        conn.close()
        return jsonify({'total': 0, 'avg_rating': 0, 'ratings': {}, 'categories': {}, 'recommend': {}, 'recent': []})

    ratings = {}
    categories = {}
    recommend = {}
    total_rating = 0

    for row in rows:
        r = dict(row)
        rat = str(r['rating'])
        ratings[rat] = ratings.get(rat, 0) + 1
        total_rating += r['rating'] or 0
        cat = r['category'] or 'Other'
        categories[cat] = categories.get(cat, 0) + 1
        rec = r['recommend'] or 'Maybe'
        recommend[rec] = recommend.get(rec, 0) + 1

    recent = [dict(r) for r in rows[:10]]
    avg_rating = round(total_rating / total, 1)
    conn.close()

    return jsonify({
        'total': total,
        'avg_rating': avg_rating,
        'ratings': ratings,
        'categories': categories,
        'recommend': recommend,
        'recent': recent
    })

# ── Loan Application API ──────────────────────────────────────────────────
@app.route('/api/loan/submit', methods=['POST'])
@login_required
def submit_loan_application():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['applicant_name', 'email', 'phone', 'loan_amount', 'loan_type', 
                          'employment_status', 'monthly_income']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field.replace("_", " ").title()} is required.'}), 400
        
        # Calculate DTI ratio
        loan_amount = float(data.get('loan_amount', 0))
        monthly_income = float(data.get('monthly_income', 0))
        dti_ratio = (loan_amount / 12) / monthly_income if monthly_income > 0 else 0
        
        # Calculate LTV ratio if collateral value provided
        collateral_value = float(data.get('collateral_value', 0))
        ltv_ratio = (loan_amount / collateral_value * 100) if collateral_value > 0 else 0
        
        conn = get_db()
        cursor = conn.execute('''INSERT INTO loan_applications 
            (user_id, applicant_name, email, phone, loan_amount, loan_type, employment_status, 
             employer_name, monthly_income, credit_score, collateral_type, collateral_value, 
             purpose, documents, ltv_ratio, dti_ratio, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (session['user_id'], data.get('applicant_name'), data.get('email'), data.get('phone'),
             loan_amount, data.get('loan_type'), data.get('employment_status'),
             data.get('employer_name'), monthly_income, data.get('credit_score'),
             data.get('collateral_type'), collateral_value, data.get('purpose'),
             data.get('documents'), ltv_ratio, dti_ratio, 
             datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Loan application submitted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/loan/my-applications')
@login_required
def get_my_applications():
    conn = get_db()
    apps = conn.execute('''SELECT * FROM loan_applications 
                          WHERE user_id = ? ORDER BY submitted_at DESC''', 
                       (session['user_id'],)).fetchall()
    conn.close()
    return jsonify({'success': True, 'applications': [dict(app) for app in apps]})

# ── Appraiser API ──────────────────────────────────────────────────────────
@app.route('/api/appraiser/applications')
@login_required
def get_appraiser_applications():
    if session.get('user_role') != 'appraiser':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    conn = get_db()
    apps = conn.execute('''SELECT la.*, u.name as applicant_user_name 
                          FROM loan_applications la
                          LEFT JOIN users u ON la.user_id = u.id
                          ORDER BY la.submitted_at DESC''').fetchall()
    conn.close()
    return jsonify({'success': True, 'applications': [dict(app) for app in apps]})

@app.route('/api/appraiser/application/<int:app_id>')
@login_required
def get_application_detail(app_id):
    if session.get('user_role') != 'appraiser':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    conn = get_db()
    app = conn.execute('SELECT * FROM loan_applications WHERE id = ?', (app_id,)).fetchone()
    if not app:
        conn.close()
        return jsonify({'success': False, 'message': 'Application not found'}), 404
    
    # Get appraisal activities
    activities = conn.execute('''SELECT aa.*, u.name as appraiser_name 
                                FROM appraisal_activities aa
                                LEFT JOIN users u ON aa.appraiser_id = u.id
                                WHERE aa.loan_application_id = ?
                                ORDER BY aa.performed_at DESC''', (app_id,)).fetchall()
    
    # Get document requests
    doc_requests = conn.execute('''SELECT * FROM document_requests 
                                  WHERE loan_application_id = ?
                                  ORDER BY requested_at DESC''', (app_id,)).fetchall()
    conn.close()
    
    return jsonify({
        'success': True, 
        'application': dict(app),
        'activities': [dict(a) for a in activities],
        'document_requests': [dict(d) for d in doc_requests]
    })

@app.route('/api/appraiser/start-appraisal/<int:app_id>', methods=['POST'])
@login_required
def start_appraisal(app_id):
    if session.get('user_role') != 'appraiser':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        conn = get_db()
        # Update application
        conn.execute('''UPDATE loan_applications 
                       SET appraisal_status = 'in_progress', 
                           appraiser_id = ?,
                           appraisal_started_at = ?
                       WHERE id = ?''',
                    (session['user_id'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), app_id))
        
        # Log activity
        conn.execute('''INSERT INTO appraisal_activities 
                       (loan_application_id, appraiser_id, activity_type, description, performed_at)
                       VALUES (?, ?, ?, ?, ?)''',
                    (app_id, session['user_id'], 'appraisal_started', 
                     'Appraisal process initiated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Appraisal started successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/appraiser/complete-appraisal/<int:app_id>', methods=['POST'])
@login_required
def complete_appraisal(app_id):
    if session.get('user_role') != 'appraiser':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.json
        validity_flag = data.get('validity_flag')  # 'valid' or 'invalid'
        notes = data.get('notes', '')
        
        if not validity_flag or not notes:
            return jsonify({'success': False, 'message': 'Validity flag and notes are required'}), 400
        
        conn = get_db()
        # Update application
        new_status = 'approved' if validity_flag == 'valid' else 'rejected'
        conn.execute('''UPDATE loan_applications 
                       SET appraisal_status = 'completed',
                           status = ?,
                           validity_flag = ?,
                           appraiser_notes = ?,
                           appraisal_completed_at = ?
                       WHERE id = ?''',
                    (new_status, validity_flag, notes, 
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S'), app_id))
        
        # Log activity
        conn.execute('''INSERT INTO appraisal_activities 
                       (loan_application_id, appraiser_id, activity_type, description, performed_at)
                       VALUES (?, ?, ?, ?, ?)''',
                    (app_id, session['user_id'], 'appraisal_completed', 
                     f'Appraisal completed. Decision: {validity_flag}. Notes: {notes}',
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Appraisal completed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/appraiser/request-documents/<int:app_id>', methods=['POST'])
@login_required
def request_documents(app_id):
    if session.get('user_role') != 'appraiser':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.json
        document_type = data.get('document_type')
        message = data.get('message')
        
        if not document_type or not message:
            return jsonify({'success': False, 'message': 'Document type and message are required'}), 400
        
        conn = get_db()
        conn.execute('''INSERT INTO document_requests 
                       (loan_application_id, appraiser_id, document_type, request_message, requested_at)
                       VALUES (?, ?, ?, ?, ?)''',
                    (app_id, session['user_id'], document_type, message,
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Log activity
        conn.execute('''INSERT INTO appraisal_activities 
                       (loan_application_id, appraiser_id, activity_type, description, performed_at)
                       VALUES (?, ?, ?, ?, ?)''',
                    (app_id, session['user_id'], 'document_requested', 
                     f'Requested additional document: {document_type}',
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Document request sent successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/appraiser/add-note/<int:app_id>', methods=['POST'])
@login_required
def add_appraisal_note(app_id):
    if session.get('user_role') != 'appraiser':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.json
        note = data.get('note')
        activity_type = data.get('activity_type', 'note_added')
        
        if not note:
            return jsonify({'success': False, 'message': 'Note is required'}), 400
        
        conn = get_db()
        conn.execute('''INSERT INTO appraisal_activities 
                       (loan_application_id, appraiser_id, activity_type, description, performed_at)
                       VALUES (?, ?, ?, ?, ?)''',
                    (app_id, session['user_id'], activity_type, note,
                     datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Note added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    init_db()
    print("✅ Server running at http://localhost:5000")
    app.run(debug=True)