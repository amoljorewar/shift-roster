from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime

# Initialize the app and database
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shift_roster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Define Shift Types
SHIFT_TYPES = {
    'Morning': {'start': '06:00 AM', 'end': '03:00 PM'},
    'Afternoon': {'start': '12:00 PM', 'end': '09:00 PM'},
    'General': {'start': '09:00 AM', 'end': '06:00 PM'}
}

# User model with Flask-Login integration
class User(db.Model, UserMixin):  # Inherit from UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # Role for admin/employee

    def get_id(self):
        return str(self.id)  # Return the user id as a string

# Shift model
class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_name = db.Column(db.String(120), nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(120), nullable=False)
    shift_time = db.Column(db.String(50), nullable=False)

# Routes and app logic

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Load user by ID

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
            session['user_id'] = user.id  # Set the user_id in the session
            session['role'] = user.role  # Optionally, store the role too
            login_user(user)  # Login the user with Flask-Login
            return redirect(url_for('index'))  # Redirect to home page after successful login
        else:
            flash('Login failed. Check your username and password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)  # Clear user role if necessary
    logout_user()  # Logout the user from Flask-Login
    return redirect(url_for('login'))

@app.route('/users')
@login_required
def users():
    if current_user.role != 'admin':
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for('index'))

    # Query all users from the database
    users = User.query.all()

    # Render the users.html template, passing the list of users
    return render_template('users.html', users=users)

@app.route('/change_role/<int:user_id>', methods=['GET', 'POST'])
@login_required
def change_role(user_id):
    if current_user.role != 'admin':
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_role = request.form['role']
        if new_role in ['admin', 'employee']:  # Allow only valid roles
            user.role = new_role
            db.session.commit()
            flash("User role updated successfully.", "success")
            return redirect(url_for('users'))  # Redirect to the user list page

    return render_template('change_role.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        
        # Default role is 'employee'
        role = 'employee'
        
        # Check if the current logged-in user is an admin and if they are trying to register as an admin
        if 'role_admin' in request.form:  # Check if the admin checkbox was checked
            # Allow admin role if the logged-in user is an admin
            role = 'admin'

        # Check if user exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.')
        else:
            # Create new user
            new_user = User(username=username, password=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.')
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/add_shift', methods=['GET', 'POST'])
@login_required
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
@login_required
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
@login_required
def delete_shift(id):
    shift = Shift.query.get(id)
    db.session.delete(shift)
    db.session.commit()
    flash('Shift deleted successfully!')
    return redirect(url_for('index'))

@app.route('/calendar')
@login_required
def calendar_view():
    # Get current month and year
    current_date = datetime.now()
    month = current_date.month
    year = current_date.year
    month_name = current_date.strftime('%B')

    # Get shifts for the current month
    shifts = Shift.query.filter(Shift.date.like(f'{year}-{month:02d}%')).all()

    # Color mapping for shift types
    shift_colors = {
        'Morning': '#add8e6',  # Light Blue for Morning shifts
        'Afternoon': '#f4a300',  # Orange for Afternoon shifts
        'General': '#90ee90'  # Light Green for General shifts
    }

    # Format shifts for FullCalendar
    calendar_events = []
    for shift in shifts:
        shift_date = datetime.strptime(shift.date, '%Y-%m-%d').date()

        # Set shift start and end times based on the shift type
        shift_start_time = SHIFT_TYPES[shift.shift_type]['start']
        shift_end_time = SHIFT_TYPES[shift.shift_type]['end']

        # Convert start and end times to datetime objects
        start_time = datetime.strptime(f"{shift.date} {shift_start_time}", "%Y-%m-%d %I:%M %p")
        end_time = datetime.strptime(f"{shift.date} {shift_end_time}", "%Y-%m-%d %I:%M %p")

        # Determine the color based on the shift type
        color = shift_colors.get(shift.shift_type, '#378006')  # Default color if not found

        calendar_events.append({
            'title': f"{shift.employee_name} - {shift.shift_type}",
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'color': color  # Set the color for each event
        })

    return render_template('calendar.html', events=calendar_events, month_name=month_name, month=month, year=year)

# Initialize the database
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # Ensure Flask is listening on all IPs
