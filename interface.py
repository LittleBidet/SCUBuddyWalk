from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import time
import threading
from functools import wraps  # Ensures Flask routes work correctly with decorators

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Initialize Database
def init_db():
    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, phone_number TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS walks (
            id INTEGER PRIMARY KEY, user_id INTEGER, people_count INTEGER, 
            start_location TEXT, destination TEXT, departure_time INTEGER, 
            description TEXT, phone_number TEXT, timestamp INTEGER, 
            FOREIGN KEY(user_id) REFERENCES users(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS walk_participants (
            id INTEGER PRIMARY KEY, walk_id INTEGER, user_email TEXT, 
            description TEXT, phone_number TEXT, 
            FOREIGN KEY(walk_id) REFERENCES walks(id))''')
        conn.commit()

# Function to remove expired walks
def remove_expired_walks():
    while True:
        current_time = int(time.time())
        with sqlite3.connect('walks.db') as conn:
            c = conn.cursor()
            c.execute("DELETE FROM walks WHERE timestamp <= ?", (current_time,))
            conn.commit()
        time.sleep(60)  # Check every 60 seconds

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper

# Routes
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    phone_number = request.form.get('phone_number', '')
    if "@scu.edu" not in email:
        flash("Invalid Email! Must use SCU email.", "error")
        return redirect(url_for('index'))

    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (email, phone_number) VALUES (?, ?)", (email, phone_number))
        conn.commit()
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        user_id = c.fetchone()[0]
        session['user_id'] = user_id
        session['email'] = email
        session['phone_number'] = phone_number

    return redirect(url_for('home'))

@app.route('/home')
@login_required
def home():
    return render_template('requestwalk.html')

@app.route('/cancel_walk/<int:walk_id>', methods=['POST'])
@login_required
def cancel_walk(walk_id):
    user_id = session['user_id']
    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM walks WHERE id = ? AND user_id = ?", (walk_id, user_id))
        c.execute("DELETE FROM walk_participants WHERE walk_id = ?", (walk_id,))
        conn.commit()
    return redirect(url_for('list_walks'))

@app.route('/leave_walk/<int:walk_id>', methods=['POST'])
@login_required
def leave_walk(walk_id):
    user_email = session['email']
    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM walk_participants WHERE walk_id = ? AND user_email = ?", (walk_id, user_email))
        conn.commit()
    return redirect(url_for('list_walks'))

@app.route('/walks')
@login_required
def list_walks():
    current_time = int(time.time())
    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM walks WHERE timestamp > ? ORDER BY timestamp ASC", (current_time,))
        walks = c.fetchall()
    return render_template('walksrequested.html', walks=walks)

@app.route('/walks_data')
@login_required
def walks_data():
    current_time = int(time.time())
    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, start_location, destination, timestamp FROM walks WHERE timestamp > ?", (current_time,))
        walks = c.fetchall()
    return jsonify(walks)

@app.route('/walk/<int:walk_id>')
@login_required
def walk_details(walk_id):
    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM walks WHERE id = ?", (walk_id,))
        walk = c.fetchone()
        c.execute("SELECT user_email, description, phone_number FROM walk_participants WHERE walk_id = ?", (walk_id,))
        participants = c.fetchall()
    return render_template('walk_details.html', walk=walk, participants=participants)

@app.route('/map')
@login_required
def map_view():
    return render_template('mapinterface.html')

@app.route('/request_walk', methods=['POST'])
@login_required
def request_walk():
    user_id = session['user_id']
    email = session['email']
    phone_number = session['phone_number']
    people_count = request.form.get('people_count')
    start_location = request.form.get('start_location')
    destination = request.form.get('destination')
    departure_time = int(request.form.get('departure_time'))
    description = request.form.get('description')
    expiration_time = int(time.time()) + (departure_time * 60)

    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO walks 
                     (user_id, people_count, start_location, destination, 
                      departure_time, description, phone_number, timestamp) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
                  (user_id, people_count, start_location, destination, 
                   departure_time, description, phone_number, expiration_time))
        walk_id = c.lastrowid
        c.execute("INSERT INTO walk_participants (walk_id, user_email, description, phone_number) VALUES (?, ?, ?, ?)",
                  (walk_id, email, description, phone_number))
        conn.commit()

    return redirect(url_for('list_walks'))


@app.route('/join_walk/<int:walk_id>', methods=['GET', 'POST'])
@login_required
def join_walk(walk_id):
    if request.method == 'POST':
        user_email = session.get('email', 'Anonymous')
        description = request.form.get('description')
        phone_number = request.form.get('phone_number', '')

        with sqlite3.connect('walks.db') as conn:
            c = conn.cursor()
            c.execute("INSERT INTO walk_participants (walk_id, user_email, description, phone_number) VALUES (?, ?, ?, ?)", 
                      (walk_id, user_email, description, phone_number))
            conn.commit()

        return redirect(url_for('walk_details', walk_id=walk_id))
    return render_template('join_walk.html', walk_id=walk_id)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/signout')
def signout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    threading.Thread(target=remove_expired_walks, daemon=True).start()
    app.run(debug=True)


def leave_walk(walk_id):
   """
   Allows a user to leave a walk they joined but did not request.
   """
   user_email = session['email']
   with sqlite3.connect('walks.db') as conn:
       c = conn.cursor()
       # Remove only the participant's entry, not the entire walk
       c.execute("DELETE FROM walk_participants WHERE walk_id = ? AND user_email = ?", (walk_id, user_email))
       conn.commit()
   flash("You have successfully left the walk.", "success")
   return redirect(url_for('list_walks'))
