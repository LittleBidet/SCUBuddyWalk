from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def init_db():
    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE)''')
        c.execute('''CREATE TABLE IF NOT EXISTS walks (
            id INTEGER PRIMARY KEY, user_id INTEGER, people_count INTEGER, 
            start_location TEXT, destination TEXT, departure_time TEXT, 
            description TEXT, phone_visible INTEGER, 
            FOREIGN KEY(user_id) REFERENCES users(id))''')
        conn.commit()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    if "@scu.edu" not in email:
        return "Invalid Email! Must use SCU email."
    
    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (email) VALUES (?)", (email,))
        conn.commit()
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        user_id = c.fetchone()[0]
        session['user_id'] = user_id
        session['email'] = email
    
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('requestwalk.html')

@app.route('/request_walk', methods=['POST'])
def request_walk():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    people_count = request.form.get('people_count')
    start_location = request.form.get('start_location')
    destination = request.form.get('destination')
    departure_time = request.form.get('departure_time')
    description = request.form.get('description')
    phone_visible = 1 if 'phone_visible' in request.form else 0
    
    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO walks 
                     (user_id, people_count, start_location, destination, 
                      departure_time, description, phone_visible) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                  (user_id, people_count, start_location, destination, 
                   departure_time, description, phone_visible))
        conn.commit()
    
    return redirect(url_for('home'))

@app.route('/walks')
def list_walks():
    with sqlite3.connect('walks.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM walks")
        walks = c.fetchall()
    return render_template('walksrequested.html', walks=walks)

@app.route('/map')
def map_view():
    return render_template('mapinterface.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
