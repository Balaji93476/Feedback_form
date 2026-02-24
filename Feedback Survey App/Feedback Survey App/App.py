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

if __name__ == '__main__':
    init_db()
    print("✅ Server running at http://localhost:5000")
    app.run(debug=True)