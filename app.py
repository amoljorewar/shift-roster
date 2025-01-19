from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import calendar
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shift_roster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define Shift Types
SHIFT_TYPES = {
    'Morning': {'start': '06:00 AM', 'end': '03:00 PM'},
    'Afternoon': {'start': '12:00 PM', 'end': '09:00 PM'},
    'General': {'start': '09:00 AM', 'end': '06:00 PM'}
}

# User and Shift models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # Role for admin/employee

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_name = db.Column(db.String(120), nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(120), nullable=False)
    shift_time = db.Column(db.String(50), nullable=False)

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    shifts = Shift.query.all()
    return render_template('index.html', shifts=shifts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role  # Store user role in session
            return redirect(url_for('index'))  # After successful login, redirect to index
        else:
            flash('Login failed. Check your username and password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)  # Ensure the role is also cleared from the session
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = 'admin' if 'role_admin' in request.form else 'employee'

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.')
        else:
            new_user = User(username=username, password=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.')
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/add_shift', methods=['GET', 'POST'])
def add_shift():
    if request.method == 'POST':
        employee_name = request.form['employee_name']
        shift_type = request.form['shift_type']
        date = request.form['date']

        # Prevent double-booking
        existing_shift = Shift.query.filter_by(employee_name=employee_name, date=date).first()
        if existing_shift:
            flash('This employee is already scheduled for a shift on this date.')
        else:
            shift_time = SHIFT_TYPES[shift_type]['start'] + ' - ' + SHIFT_TYPES[shift_type]['end']
            new_shift = Shift(employee_name=employee_name, shift_type=shift_type, date=date, shift_time=shift_time)
            db.session.add(new_shift)
            db.session.commit()
            return redirect(url_for('index'))

    return render_template('add_shift.html', shift_types=SHIFT_TYPES.keys())

@app.route('/edit_shift/<int:id>', methods=['GET', 'POST'])
def edit_shift(id):
    shift = Shift.query.get(id)
    if request.method == 'POST':
        shift.employee_name = request.form['employee_name']
        shift.shift_type = request.form['shift_type']
        shift.date = request.form['date']
        shift.shift_time = SHIFT_TYPES[shift.shift_type]['start'] + ' - ' + SHIFT_TYPES[shift.shift_type]['end']
        
        db.session.commit()
        flash('Shift updated successfully!')
        return redirect(url_for('index'))

    return render_template('edit_shift.html', shift=shift, shift_types=SHIFT_TYPES.keys())

@app.route('/delete_shift/<int:id>')
def delete_shift(id):
    shift = Shift.query.get(id)
    db.session.delete(shift)
    db.session.commit()
    flash('Shift deleted successfully!')
    return redirect(url_for('index'))

# Show shift roster in calendar view
@app.route('/calendar')
def calendar_view():
    # Get current month and year
    current_date = datetime.now()
    month = current_date.month
    year = current_date.year
    month_name = current_date.strftime('%B')

    # Get shifts for the current month
    shifts = Shift.query.filter(Shift.date.like(f'{year}-{month:02d}%')).all()

    # Format shifts for FullCalendar
    calendar_events = []
    for shift in shifts:
        shift_date = datetime.strptime(shift.date, '%Y-%m-%d').date()
        calendar_events.append({
            'title': f"{shift.employee_name} - {shift.shift_type}",
            'start': shift_date.strftime('%Y-%m-%d') + "T09:00:00",
            'end': shift_date.strftime('%Y-%m-%d') + "T18:00:00"
        })

    return render_template('calendar.html', events=calendar_events, month_name=month_name, month=month, year=year)

# Initialize the database
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # Ensure Flask is listening on all IPs

