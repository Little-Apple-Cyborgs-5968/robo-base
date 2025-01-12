import datetime
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import psycopg2
from psycopg2.extras import DictCursor
import os


app = Flask(__name__)
app.secret_key = os.urandom(24)

DATABASE_URL = os.environ.get('DATABASE_URL')

# Master account creds
MASTER_FULL_NAME = "admin"
MASTER_PASSWORD = "masterpassword"

# initial page
@app.route('/')
def index():
    return redirect(url_for('login'))

# Helper function to get database connection
def get_db():
    if not hasattr(g, "db_conn"):
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL isn't set. Check the environment variables.")
        g.db_conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.DictCursor  # Use DictCursor for dictionary-like rows
        )
    return g.db_conn



@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db_conn', None)
    if db is not None:
        db.close()

@app.route('/dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Fetch all entries for the logged-in user
    cursor.execute('SELECT entry_id AS id, date, hours FROM entries WHERE user_id = %s ORDER BY date', (user_id,))
    logs = cursor.fetchall()

    print("---------------------------------------------------------")
    print(logs)
    print("---------------------------------------------------------")

    # Calculate total hours
    cursor.execute('SELECT COALESCE(SUM(hours), 0) AS total_hours FROM entries WHERE user_id = %s', (user_id,))
    total_hours = cursor.fetchone()['total_hours']

    return render_template('user.html', full_name=session['full_name'], logs=logs, total_hours=total_hours)

@app.route('/admin')
def admin():
    if 'user_id' in session and session['user_id'] == -1:  # Check if master account
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT users.full_name, entries.date, entries.hours '
                   'FROM users LEFT JOIN entries ON users.user_id = entries.user_id ORDER BY users.full_name, entries.date')
        logs = cursor.fetchall()

        # Calculate total hours for each account
        cursor.execute('SELECT users.full_name, COALESCE(SUM(entries.hours), 0) AS total_hours '
                   'FROM users LEFT JOIN entries ON users.user_id = entries.user_id '
                   'GROUP BY users.full_name ORDER BY users.full_name')
        total_hours = cursor.fetchall()

        return render_template('admin.html', logs=logs, total_hours=total_hours)
    return redirect(url_for('login'))

@app.route('/add_entry', methods=['GET', 'POST'])
def add_entry():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'date' in request.form and 'hours' in request.form:
            date = request.form['date']
            hours = request.form['hours']
            user_id = session['user_id']

            if date > datetime.datetime.now().strftime('%Y-%m-%d'):
                flash("Please select a valid date! (don't premove hours)", 'danger')
                return redirect(url_for('add_entry'))

            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO entries (user_id, date, hours) VALUES (%s, %s, %s)',
                (user_id, date, hours)
            )
        db.commit()
        flash('<img src="/static/thumb_robo.png" alt="Success"> Entry added successfully!', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('add_entry.html')

@app.route('/edit_entry/<int:log_id>', methods=['GET', 'POST'])
def edit_entry(log_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    # Handle the case when the user submits a POST request
    if request.method == 'POST':
        if 'date' in request.form and 'hours' in request.form:  # Edit form
            date = request.form['date']
            hours = request.form['hours']

            if date > datetime.datetime.now().strftime('%Y-%m-%d'):
                flash("Please select a valid date! (don't premove hours)", 'danger')
                return redirect(url_for('edit_entry', log_id=log_id))

            cursor.execute(
                'UPDATE entries SET date = %s, hours = %s WHERE entry_id = %s AND user_id = %s',
                (date, hours, log_id, session['user_id'])
            )
            
            db.commit()
            flash('Entry updated successfully!', 'success')
            return redirect(url_for('user_dashboard'))

        if 'delete' in request.form:  # If delete form is submitted
            cursor.execute('DELETE FROM entries WHERE entry_id = %s AND user_id = %s', (log_id, session['user_id']))
            db.commit()
            flash('Entry deleted successfully!', 'danger')
            return redirect(url_for('user_dashboard'))

    # Fetch the entry to edit
    cursor.execute('SELECT * FROM entries WHERE entry_id = %s AND user_id = %s', (log_id, session['user_id']))
    entry = cursor.fetchone()
    if not entry:
        flash('Entry not found or access denied.', 'danger')
        return redirect(url_for('user_dashboard'))

    return render_template('edit_entry.html', entry=entry)



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form['full_name']
        password = request.form['password']  # Store as plain text for simplicity

        db = get_db()
        cursor = db.cursor()

        try:
            cursor.execute('INSERT INTO users (full_name, password) VALUES (%s, %s)',
                           (full_name, password))
            db.commit()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            db.rollback()
            flash('Account under this name already exists!', 'danger')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        full_name = request.form['full_name']
        password = request.form['password']

        # Check if master account
        if full_name == MASTER_FULL_NAME and password == MASTER_PASSWORD:
            session['user_id'] = -1  # Special ID for master account
            session['full_name'] = MASTER_FULL_NAME
            return redirect(url_for('admin'))

        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE full_name = %s', (full_name,))
        user = cursor.fetchone()

        if user and user['password'] == password:
            session['user_id'] = user['user_id']    
            session['full_name'] = user['full_name']
            return redirect(url_for('user_dashboard'))  # Redirect to user dashboard
        flash('Invalid credentials!', 'danger')

    return render_template('login.html')


@app.route('/log', methods=['POST'])
def log_hours():
    if 'user_id' not in session or session['user_id'] == -1:
        return redirect(url_for('login'))

    date = request.form['date']
    hours = request.form['hours']
    
    if date > datetime.now().strftime('%Y-%m-%d'):
        flash('Please select a valid date!', 'danger')
        return redirect(url_for('add_entry'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO entries (user_id, date, hours) VALUES (%s, %s, %s)',
        (session['user_id'], date, hours)
    )
    db.commit()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)