from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import sqlite3
import hashlib
from datetime import datetime
from functools import wraps
import secrets

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
    
    # Loan Management Tables
    c.execute('''CREATE TABLE IF NOT EXISTS borrowers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_details TEXT NOT NULL,
        email TEXT,
        loan_account_number TEXT UNIQUE,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        bank_account_number TEXT NOT NULL,
        bank_name TEXT NOT NULL,
        branch_details TEXT NOT NULL,
        contact_details TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS loan_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id TEXT UNIQUE NOT NULL,
        borrower_id INTEGER NOT NULL,
        agent_id INTEGER NOT NULL,
        loan_amount REAL NOT NULL,
        loan_type TEXT NOT NULL,
        loan_term INTEGER NOT NULL,
        interest_rate REAL NOT NULL,
        payment_method TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        approval_date TEXT,
        applicable_fees REAL DEFAULT 0,
        disbursement_amount REAL,
        created_at TEXT,
        FOREIGN KEY (borrower_id) REFERENCES borrowers(id),
        FOREIGN KEY (agent_id) REFERENCES agents(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS payment_vouchers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_reference_number TEXT UNIQUE NOT NULL,
        loan_id TEXT NOT NULL,
        loan_application_id INTEGER NOT NULL,
        voucher_creation_timestamp TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        FOREIGN KEY (loan_application_id) REFERENCES loan_applications(id)
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

# ── Auth API ───────────────────────────────────────────────────────────────────

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm = data.get('confirm_password', '')

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

    conn.execute('INSERT INTO users (name, email, password, created_at) VALUES (?, ?, ?, ?)',
                 (name, email, hash_password(password), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
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

# ── Loan Management Helper Functions ──────────────────────────────────────

def generate_voucher_reference_number():
    """Generate a unique voucher reference number following organizational convention"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_part = secrets.token_hex(4).upper()
    return f"PV-{timestamp}-{random_part}"

def generate_loan_id():
    """Generate a unique loan ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = secrets.token_hex(3).upper()
    return f"LN-{timestamp}-{random_part}"

def generate_loan_account_number():
    """Generate a unique loan account number"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_part = secrets.token_hex(4).upper()
    return f"LA-{timestamp}-{random_part}"

def validate_loan_data(loan_data, borrower_data, agent_data):
    """Validate that all required loan, borrower, and agent data is present"""
    errors = []
    
    # Validate loan data
    required_loan_fields = ['loan_amount', 'loan_type', 'loan_term', 'interest_rate', 'payment_method']
    for field in required_loan_fields:
        if field not in loan_data or not loan_data[field]:
            errors.append(f"Loan {field.replace('_', ' ')} is required")
    
    # Validate borrower data
    required_borrower_fields = ['name', 'contact_details']
    for field in required_borrower_fields:
        if field not in borrower_data or not borrower_data[field]:
            errors.append(f"Borrower {field.replace('_', ' ')} is required")
    
    # Validate agent data
    required_agent_fields = ['name', 'bank_account_number', 'bank_name', 'branch_details']
    for field in required_agent_fields:
        if field not in agent_data or not agent_data[field]:
            errors.append(f"Agent {field.replace('_', ' ')} is required")
    
    return errors

def generate_payment_voucher(loan_application_id):
    """Generate payment voucher for approved loan"""
    conn = get_db()
    
    # Get loan application details with borrower and agent info
    loan = conn.execute('''
        SELECT la.*, b.name as borrower_name, b.contact_details as borrower_contact,
               b.email as borrower_email, b.loan_account_number,
               a.name as agent_name, a.bank_account_number, a.bank_name, a.branch_details
        FROM loan_applications la
        JOIN borrowers b ON la.borrower_id = b.id
        JOIN agents a ON la.agent_id = a.id
        WHERE la.id = ?
    ''', (loan_application_id,)).fetchone()
    
    if not loan:
        conn.close()
        return {'success': False, 'message': 'Loan application not found'}
    
    loan_dict = dict(loan)
    
    # Validate all required fields are present
    validation_errors = []
    
    # Check loan details
    if not all([loan_dict.get('loan_id'), loan_dict.get('loan_amount'), 
                loan_dict.get('loan_type'), loan_dict.get('loan_term'),
                loan_dict.get('interest_rate'), loan_dict.get('approval_date'),
                loan_dict.get('payment_method')]):
        validation_errors.append('Loan details are incomplete')
    
    # Check borrower information
    if not all([loan_dict.get('borrower_name'), loan_dict.get('borrower_contact'),
                loan_dict.get('loan_account_number')]):
        validation_errors.append('Borrower information is incomplete')
    
    # Check agent information
    if not all([loan_dict.get('agent_name'), loan_dict.get('bank_account_number'),
                loan_dict.get('bank_name'), loan_dict.get('branch_details')]):
        validation_errors.append('Agent account information is incomplete')
    
    # Check disbursement amount is calculated
    if loan_dict.get('disbursement_amount') is None:
        validation_errors.append('Disbursement amount is not calculated')
    
    if validation_errors:
        conn.close()
        return {
            'success': False,
            'message': 'Cannot generate payment voucher. Missing required information: ' + ', '.join(validation_errors)
        }
    
    # Check if voucher already exists
    existing_voucher = conn.execute(
        'SELECT * FROM payment_vouchers WHERE loan_application_id = ?',
        (loan_application_id,)
    ).fetchone()
    
    if existing_voucher:
        conn.close()
        return {
            'success': False,
            'message': 'Payment voucher already exists for this loan application'
        }
    
    # Generate voucher
    voucher_ref = generate_voucher_reference_number()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn.execute('''
        INSERT INTO payment_vouchers 
        (voucher_reference_number, loan_id, loan_application_id, voucher_creation_timestamp, generated_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (voucher_ref, loan_dict['loan_id'], loan_application_id, timestamp, timestamp))
    
    conn.commit()
    conn.close()
    
    return {
        'success': True,
        'message': 'Payment voucher generated successfully',
        'voucher_reference_number': voucher_ref,
        'voucher_data': {
            'voucher_reference_number': voucher_ref,
            'voucher_creation_timestamp': timestamp,
            'loan_id': loan_dict['loan_id'],
            'loan_amount': loan_dict['loan_amount'],
            'loan_type': loan_dict['loan_type'],
            'loan_term': loan_dict['loan_term'],
            'interest_rate': loan_dict['interest_rate'],
            'approval_date': loan_dict['approval_date'],
            'payment_method': loan_dict['payment_method'],
            'disbursement_amount': loan_dict['disbursement_amount'],
            'applicable_fees': loan_dict['applicable_fees'],
            'borrower_name': loan_dict['borrower_name'],
            'borrower_id': loan_dict['borrower_id'],
            'borrower_contact': loan_dict['borrower_contact'],
            'borrower_email': loan_dict['borrower_email'],
            'loan_account_number': loan_dict['loan_account_number'],
            'agent_name': loan_dict['agent_name'],
            'agent_id': loan_dict['agent_id'],
            'agent_bank_account_number': loan_dict['bank_account_number'],
            'agent_bank_name': loan_dict['bank_name'],
            'agent_branch_details': loan_dict['branch_details']
        }
    }

# ── Loan Management Page Routes ───────────────────────────────────────────

@app.route('/loans')
@login_required
def loans_page():
    return render_template('loans.html', user_name=session.get('user_name'))

@app.route('/vouchers')
@login_required
def vouchers_page():
    return render_template('vouchers.html', user_name=session.get('user_name'))

# ── Loan Management API ────────────────────────────────────────────────────

@app.route('/api/borrowers', methods=['POST'])
@login_required
def create_borrower():
    """Create a new borrower"""
    data = request.json
    name = data.get('name', '').strip()
    contact_details = data.get('contact_details', '').strip()
    email = data.get('email', '').strip()
    
    if not name or not contact_details:
        return jsonify({'success': False, 'message': 'Name and contact details are required'})
    
    loan_account_number = generate_loan_account_number()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db()
    conn.execute('''
        INSERT INTO borrowers (name, contact_details, email, loan_account_number, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, contact_details, email, loan_account_number, created_at))
    conn.commit()
    
    borrower = conn.execute('SELECT * FROM borrowers WHERE loan_account_number = ?', (loan_account_number,)).fetchone()
    conn.close()
    
    return jsonify({'success': True, 'borrower': dict(borrower)})

@app.route('/api/agents', methods=['POST'])
@login_required
def create_agent():
    """Create a new agent"""
    data = request.json
    name = data.get('name', '').strip()
    bank_account_number = data.get('bank_account_number', '').strip()
    bank_name = data.get('bank_name', '').strip()
    branch_details = data.get('branch_details', '').strip()
    contact_details = data.get('contact_details', '').strip()
    
    if not all([name, bank_account_number, bank_name, branch_details]):
        return jsonify({'success': False, 'message': 'All agent details are required'})
    
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db()
    conn.execute('''
        INSERT INTO agents (name, bank_account_number, bank_name, branch_details, contact_details, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, bank_account_number, bank_name, branch_details, contact_details, created_at))
    conn.commit()
    
    agent = conn.execute('SELECT * FROM agents WHERE id = last_insert_rowid()').fetchone()
    conn.close()
    
    return jsonify({'success': True, 'agent': dict(agent)})

@app.route('/api/loans', methods=['POST'])
@login_required
def create_loan_application():
    """Create a new loan application"""
    data = request.json
    
    # Extract data
    borrower_id = data.get('borrower_id')
    agent_id = data.get('agent_id')
    loan_amount = data.get('loan_amount')
    loan_type = data.get('loan_type', '').strip()
    loan_term = data.get('loan_term')
    interest_rate = data.get('interest_rate')
    payment_method = data.get('payment_method', '').strip()
    applicable_fees = data.get('applicable_fees', 0)
    
    # Validate required fields
    if not all([borrower_id, agent_id, loan_amount, loan_type, loan_term, interest_rate, payment_method]):
        return jsonify({'success': False, 'message': 'All loan details are required'})
    
    try:
        loan_amount = float(loan_amount)
        loan_term = int(loan_term)
        interest_rate = float(interest_rate)
        applicable_fees = float(applicable_fees)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid numeric values for amount, term, rate, or fees'})
    
    # Calculate disbursement amount
    disbursement_amount = loan_amount - applicable_fees
    
    # Generate loan ID
    loan_id = generate_loan_id()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db()
    
    # Verify borrower and agent exist
    borrower = conn.execute('SELECT * FROM borrowers WHERE id = ?', (borrower_id,)).fetchone()
    agent = conn.execute('SELECT * FROM agents WHERE id = ?', (agent_id,)).fetchone()
    
    if not borrower:
        conn.close()
        return jsonify({'success': False, 'message': 'Borrower not found'})
    
    if not agent:
        conn.close()
        return jsonify({'success': False, 'message': 'Agent not found'})
    
    # Create loan application
    conn.execute('''
        INSERT INTO loan_applications 
        (loan_id, borrower_id, agent_id, loan_amount, loan_type, loan_term, 
         interest_rate, payment_method, status, applicable_fees, disbursement_amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
    ''', (loan_id, borrower_id, agent_id, loan_amount, loan_type, loan_term,
          interest_rate, payment_method, applicable_fees, disbursement_amount, created_at))
    
    conn.commit()
    
    loan = conn.execute('SELECT * FROM loan_applications WHERE loan_id = ?', (loan_id,)).fetchone()
    conn.close()
    
    return jsonify({'success': True, 'loan': dict(loan)})

@app.route('/api/loans/<int:loan_id>/approve', methods=['POST'])
@login_required
def approve_loan(loan_id):
    """Approve a loan application and automatically generate payment voucher"""
    conn = get_db()
    
    # Get loan application
    loan = conn.execute('SELECT * FROM loan_applications WHERE id = ?', (loan_id,)).fetchone()
    
    if not loan:
        conn.close()
        return jsonify({'success': False, 'message': 'Loan application not found'})
    
    loan_dict = dict(loan)
    
    if loan_dict['status'] == 'approved':
        conn.close()
        return jsonify({'success': False, 'message': 'Loan already approved'})
    
    # Update loan status to approved
    approval_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('''
        UPDATE loan_applications 
        SET status = 'approved', approval_date = ?
        WHERE id = ?
    ''', (approval_date, loan_id))
    conn.commit()
    conn.close()
    
    # Automatically generate payment voucher
    voucher_result = generate_payment_voucher(loan_id)
    
    if voucher_result['success']:
        return jsonify({
            'success': True,
            'message': 'Loan approved and payment voucher generated successfully',
            'voucher_reference_number': voucher_result['voucher_reference_number'],
            'voucher_data': voucher_result['voucher_data']
        })
    else:
        return jsonify({
            'success': False,
            'message': f"Loan approved but voucher generation failed: {voucher_result['message']}"
        })

@app.route('/api/loans')
@login_required
def get_loans():
    """Get all loan applications"""
    conn = get_db()
    rows = conn.execute('''
        SELECT la.*, b.name as borrower_name, b.loan_account_number,
               a.name as agent_name, a.bank_name
        FROM loan_applications la
        JOIN borrowers b ON la.borrower_id = b.id
        JOIN agents a ON la.agent_id = a.id
        ORDER BY la.created_at DESC
    ''').fetchall()
    conn.close()
    
    loans = [dict(row) for row in rows]
    return jsonify({'success': True, 'loans': loans})

@app.route('/api/vouchers')
@login_required
def get_vouchers():
    """Get all payment vouchers"""
    conn = get_db()
    rows = conn.execute('''
        SELECT pv.*, la.loan_id, la.loan_amount, la.loan_type, la.disbursement_amount,
               la.payment_method, la.approval_date, la.applicable_fees,
               la.loan_term, la.interest_rate,
               b.name as borrower_name, b.contact_details as borrower_contact,
               b.email as borrower_email, b.loan_account_number,
               a.name as agent_name, a.bank_account_number, a.bank_name, a.branch_details
        FROM payment_vouchers pv
        JOIN loan_applications la ON pv.loan_application_id = la.id
        JOIN borrowers b ON la.borrower_id = b.id
        JOIN agents a ON la.agent_id = a.id
        ORDER BY pv.generated_at DESC
    ''').fetchall()
    conn.close()
    
    vouchers = [dict(row) for row in rows]
    return jsonify({'success': True, 'vouchers': vouchers})

@app.route('/api/borrowers')
@login_required
def get_borrowers():
    """Get all borrowers"""
    conn = get_db()
    rows = conn.execute('SELECT * FROM borrowers ORDER BY created_at DESC').fetchall()
    conn.close()
    
    borrowers = [dict(row) for row in rows]
    return jsonify({'success': True, 'borrowers': borrowers})

@app.route('/api/agents')
@login_required
def get_agents():
    """Get all agents"""
    conn = get_db()
    rows = conn.execute('SELECT * FROM agents ORDER BY created_at DESC').fetchall()
    conn.close()
    
    agents = [dict(row) for row in rows]
    return jsonify({'success': True, 'agents': agents})

if __name__ == '__main__':
    init_db()
    print("✅ Server running at http://localhost:5000")
    app.run(debug=True)