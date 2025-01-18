from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Ensure app is accessible outside the container
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shift_roster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User and Shift models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # Added user role (admin/employee)

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_name = db.Column(db.String(120), nullable=False)
    shift_time = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(120), nullable=False)

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
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check your username and password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
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
        shift_time = request.form['shift_time']
        date = request.form['date']
        
        # Prevent double-booking
        existing_shift = Shift.query.filter_by(employee_name=employee_name, date=date).first()
        if existing_shift:
            flash('This employee is already scheduled for a shift on this date.')
        else:
            new_shift = Shift(employee_name=employee_name, shift_time=shift_time, date=date)
            db.session.add(new_shift)
            db.session.commit()
            return redirect(url_for('index'))
    
    return render_template('add_shift.html')

@app.route('/edit_shift/<int:id>', methods=['GET', 'POST'])
def edit_shift(id):
    shift = Shift.query.get(id)
    if request.method == 'POST':
        shift.employee_name = request.form['employee_name']
        shift.shift_time = request.form['shift_time']
        shift.date = request.form['date']
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('edit_shift.html', shift=shift)

@app.route('/delete_shift/<int:id>')
def delete_shift(id):
    shift = Shift.query.get(id)
    db.session.delete(shift)
    db.session.commit()
    return redirect(url_for('index'))

# Export shifts to CSV (Only for Admin)
@app.route('/export_shifts')
def export_shifts():
    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        flash('You do not have permission to export shifts.')
        return redirect(url_for('index'))
    
    shifts = Shift.query.all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Employee Name', 'Shift Time', 'Date'])
    for shift in shifts:
        writer.writerow([shift.employee_name, shift.shift_time, shift.date])
    
    output.seek(0)
    return send_file(output, mimetype='text/csv', attachment_filename='shifts.csv', as_attachment=True)

# Initialize the database
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # Ensure Flask is listening on all IPs

