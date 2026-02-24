from flask import Flask, request, jsonify, render_template
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)

DB = "feedback.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        rating INTEGER,
        category TEXT,
        message TEXT,
        recommend TEXT,
        submitted_at TEXT
    )''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json
    conn = get_db()
    conn.execute('''INSERT INTO feedback (name, email, rating, category, message, recommend, submitted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (data.get('name'), data.get('email'), data.get('rating'),
                  data.get('category'), data.get('message'), data.get('recommend'),
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Feedback submitted!'})

@app.route('/api/results')
def results():
    conn = get_db()
    rows = conn.execute('SELECT * FROM feedback ORDER BY submitted_at DESC').fetchall()
    total = len(rows)
    
    if total == 0:
        return jsonify({'total': 0, 'avg_rating': 0, 'ratings': {}, 'categories': {}, 'recommend': {}, 'recent': []})

    ratings = {}
    categories = {}
    recommend = {}
    total_rating = 0

    for row in rows:
        r = dict(row)
        # Ratings distribution
        rat = str(r['rating'])
        ratings[rat] = ratings.get(rat, 0) + 1
        total_rating += r['rating'] or 0

        # Category distribution
        cat = r['category'] or 'Other'
        categories[cat] = categories.get(cat, 0) + 1

        # Recommend distribution
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