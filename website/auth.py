from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from .models import User, Role, Transactions, TeacherRequestHistory, Account, Class, Subject, JoinRequest, Coupon
from . import db
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from sqlalchemy import and_

auth = Blueprint('auth', __name__) #defines auth blueprint to create url

#//login and sign-up-------------------------------------------------------------------------------------------------------------------------------------------------------------


# Route for user login
@auth.route('/login', methods=['GET', 'POST'])
def login():
    # If user submits the login form
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        # Check if user with the entered email exists
        if user:
            # Check if the entered password matches the stored hashed password
            if check_password_hash(user.password, password):
                role = user.role
                # If user is an admin
                if role.name == "admin":
                    flash('Logged in as admin successfully!', category='success')
                    login_user(user, remember=True)
                    return redirect(url_for('auth.admin_page'))
                # If user is a teacher
                elif role.name == "teacher":
                    # If teacher's role is not yet approved
                    if not user.role_approved:
                        flash('Teacher role not approved yet.', category='error')
                        return redirect(url_for('auth.login'))
                    else:
                        flash('Logged in as teacher successfully!', category='success')
                        login_user(user, remember=True)
                        return redirect(url_for('auth.award_points'))
                # If user is a student
                elif role.name == "student":
                    flash('Logged in as student successfully!', category='success')
                    login_user(user, remember=True)
                    return redirect(url_for('auth.student', student_id=user.id))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')
    
    # Render the login page template
    return render_template('login.html', user=current_user)

# Function to calculate password strength
def password_strength(password):
    score = 0
    if len(password) >= 8:
        score += 1
    if any(char.isdigit() for char in password):
        score += 1
    if any(char.isupper() for char in password):
        score += 1
    if any(char in set(r"!@#$%^&*()/") for char in password):
        score += 1
    if score >= 4:
        return score, "Password is strong."
    else:
        missing_requirements = []
        if len(password) < 8:
            missing_requirements.append("Password must be at least 8 characters.")
        if not any(char.isdigit() for char in password):
            missing_requirements.append("Password must contain at least one digit.")
        if not any(char.isupper() for char in password):
            missing_requirements.append("Password must contain at least one uppercase letter.")
        if not any(char in set(r"!@#$%^&*()/") for char in password):
            missing_requirements.append("Password must contain at least one symbol (!@#$%^&*()/).")
        return score, ", ".join(missing_requirements)

# Function to generate a unique username
def generate_username(first_name, last_name):
    base_username = first_name[:3].lower() + last_name[:3].lower()
    username = base_username
    counter = 1

    while User.query.filter_by(user_name=username).first() is not None:
        username = base_username + str(counter)
        counter += 1

    return username

# Define a function to check if a string contains any digit
def contains_digit(s):
    return any(c.isdigit() for c in s)

# Define a route for sign up with GET and POST methods
@auth.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    # If the request method is POST, get user input data from the form
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        role = request.form.get('role')

        # Validate user input data
        if len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        # Check if first name and last name contain any digits, and their length is at least 2 characters
        elif contains_digit(first_name) or contains_digit(last_name) or len(first_name) < 2 or len(last_name) < 2:
            flash('First name and last name must not contain numbers and should be at least 2 characters long.', category='error')
        # Check if passwords match and their length requirements
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')  
        elif len(password1) > 25:
            flash('Password can only be 25 or less characters.', category='error')             
        else:
            # Check if password is strong enough
            score, message = password_strength(password1)
            if score < 4:
                flash(message, category='error')
            else:
                # Retrieve the role object with the given name from the database
                role = Role.query.filter_by(name=role).first()
                if role is None:
                    flash('Invalid role selected', category='error')
                    return redirect(url_for('auth.sign_up'))

                # Generate a username based on the first and last name
                user_name = generate_username(first_name, last_name)

                # Check if the user has requested a teacher role
                role_request = request.form.get('role') == 'teacher'
                print(role_request)

                # Create a new user object with the given information
                new_user = User(email=email, first_name=first_name, last_name=last_name, user_name=user_name, password=generate_password_hash(password1, method='sha256'), role=role, role_request=role_request, role_requested_on=datetime.now())

                try:
                    # Add the new user object to the database
                    db.session.add(new_user)
                    db.session.commit()

                    # Create a new account for the user
                    account = Account(user=new_user, balance=0)
                    db.session.add(account)
                    db.session.commit()

                except IntegrityError:
                    # If there is an integrity error (e.g. duplicate email address), rollback the transaction and show an error message
                    db.session.rollback()
                    flash('Email address already exists', category='error')
                    return redirect(url_for('auth.sign_up'))

                if role_request:
                    # If the user has requested a teacher role, create a new TeacherRequestHistory object with the user_id and status set to 'Pending'
                    teacher_request = TeacherRequestHistory(user_id=new_user.id, status='Pending')
                    db.session.add(teacher_request)
                    db.session.commit()
                    flash('Teacher role request sent. Please wait for approval.', category='success')
                    return redirect(url_for('auth.sign_up'))  # Redirect to sign-up page
                else:
                    flash('Registration successful', category='success')
                    login_user(new_user)
                    return redirect(url_for('views.home'))

    roles = Role.query.all()
    return render_template('sign_up.html', user=current_user, roles=roles)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))



#//login and sign-up-------------------------------------------------------------------------------------------------------------------------------------------------------------


#//admin--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Route for the admin page
@auth.route('/admin')
def admin_page():
    # Get all transactions
    transactions = db.session.query(Transactions).all()

    # Get all pending teacher requests
    teacher_requests = User.query.filter(User.role.has(name='teacher'), User.role_request==True).all()

    # Render the admin page and pass in the transactions and teacher_requests
    return render_template('admin.html', user=current_user, transactions=transactions, teacher_requests=teacher_requests)


# Route to update a teacher request
@auth.route('/admin/update-teacher-request', methods=['POST'])
@login_required
def update_teacher_request():
    # Get the user ID from the form
    user_id = request.form['user_id']
    # Query the user object from the database
    user = User.query.get(user_id)

    # Check if the user is valid and has a pending teacher role request
    if user is None or not user.role_request or user.role.name != 'teacher':
        flash('Invalid request.', 'error')
        return redirect(url_for('auth.admin_page'))

    # Check if the current user is an admin
    if not current_user.is_admin():
        flash('You are not authorized to approve or reject teacher requests.', 'error')
        return redirect(url_for('auth.admin_page'))

    # Get the action (approve/reject) from the form
    action = request.form['action']
    if action == 'approve':
        # Set the role_approved flag to True and role_request flag to False
        user.role_approved = True
        user.role_request = False
        # Commit the changes to the database
        db.session.commit()
        flash(f'Teacher role request for {user.email} has been approved.', 'success')
        status = 'accepted'
    elif action == 'reject':
        # Set the role_rejected flag to True and role_request flag to False
        user.role_rejected = True
        user.role_request = False
        # Commit the changes to the database
        db.session.commit()
        flash(f'Teacher role request for {user.email} has been rejected.', 'success')
        status = 'rejected'

    # Get the date_requested from the user object
    date_requested = user.role_requested_on

    # Create a new history entry for the teacher request
    history_entry = TeacherRequestHistory(
        user=user,
        status=status,
        date_resolved=datetime.utcnow(),
        resolved_by=current_user
    )
    # Add the history entry to the database and commit the changes
    db.session.add(history_entry)
    db.session.commit()
    
    # Redirect to the admin page
    return redirect(url_for('auth.admin_page'))


# Route to view teacher request history
@auth.route('/teacher_requests_history')
@login_required
def view_teacher_requests():
    # Query the teacher request history entries and order them by the date requested
    requests = TeacherRequestHistory.query.join(User, TeacherRequestHistory.user_id == User.id).order_by(User.role_requested_on).all()
    # Render the teacher requests history page and pass in the requests and the current user
    return render_template('teacher_requests_history.html', requests=requests, user=current_user)


#//admin--------------------------------------------------------------------------------------------------------------------------------------------------------------------------


#//teacher--------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Define a route for teacher 
@auth.route('/teacher')
@login_required
def teacher():
    # Query join requests and classes from database
    join_requests = JoinRequest.query.join(User).filter(User.id == 3).all()
    classes = Class.query.all()
    # Render the teacher.html template and pass the queried data to it as arguments
    return render_template('teacher_dashboard.html', user=current_user, join_requests=join_requests, classes=classes)

# Define a route for join request
@auth.route('/join_request')
@login_required
def join_request():
    # Get the value of filter query parameter, default to 'all'
    filter = request.args.get('filter', 'all')

    # Based on the value of filter, query join requests from database
    if filter == 'pending':
        join_requests = JoinRequest.query.join(User).filter(User.id == 3, JoinRequest.status == 'pending').all()
    elif filter == 'accepted_rejected':
        join_requests = JoinRequest.query.join(User).filter(User.id == 3, (JoinRequest.status == 'accepted') | (JoinRequest.status == 'rejected')).all()
    else:  # Default: Show all requests
        join_requests = JoinRequest.query.join(User).filter(User.id == 3).all()

    # Render the join_request.html template and pass the queried data and filter value to it as arguments
    return render_template('join_request.html', user=current_user, join_requests=join_requests, filter=filter)




@auth.route('/respond_join_request/<int:join_request_id>/<string:action>', methods=['GET'])
@login_required
def respond_join_request(join_request_id, action):
    # Get the join request object
    join_request = JoinRequest.query.get_or_404(join_request_id)

    # Check if the current user is the teacher of the class
    if current_user.id != join_request.class_.teacher_id:
        flash('You are not authorized to respond to this join request!', category='error')
        return redirect(url_for('auth.join_request'))

    # Update the status of the join request
    if action == 'accept':
        join_request.status = 'accepted'
        flash('Join request accepted!', category='success')
    elif action == 'reject':
        join_request.status = 'rejected'
        flash('Join request rejected!', category='success')
    else:
        flash('Invalid action!', category='error')
        return redirect(url_for('auth.join_request'))

    # Commit the changes to the database
    db.session.commit()

    # Redirect to the teacher dashboard
    return redirect(url_for('auth.join_request'))


# Define the 'award_points' function to allow an admin or teacher to award points to a student account
@auth.route('/award_points', methods=['GET', 'POST'])
@login_required  # Ensure the user is logged in
def award_points():
    
    # Check if the user is an admin or a teacher
    if current_user.is_admin() or current_user.is_teacher():
        
        # Query the database for the year groups
        year_groups = db.session.query(Class.year_group).distinct().all()
        
        # Query the database for the classes that the current user is teaching
        classes = Class.query.filter_by(teacher=current_user).all()
        
        # Query the database for all students
        students = User.query.filter_by(role_id=3).all()

        # Check if the user has submitted a form
        if request.method == 'POST':
            
            # Retrieve form data
            year_group = request.form['year_group']
            class_id = request.form['class_id']
            student_id = request.form['student_id']
            points = int(request.form['amount'])

            # Check if the user has enough points to award
            if current_user.remaining_points < points:
                flash('You do not have enough points to award.', 'danger')
                return redirect(url_for('auth.award_points'))

            # Check if the user has exceeded their weekly point limit
            if current_user.points_awarded_this_week >= current_user.weekly_point_limit:
                flash('You have exceeded your weekly point limit.', 'danger')
                return redirect(url_for('auth.award_points'))

            # Retrieve the student from the database
            student = User.query.filter_by(id=student_id, role_id=3).first()

            # Check if the student exists
            if student:
                
                # Retrieve the student's account from the database
                student_account = Account.query.filter_by(user_id=student.id).first()
                
                if student_account:
                    
                    # Update the student's account balance
                    student_account.balance += points
                    db.session.commit()

                    # Update the teacher's account points_awarded, points_awarded_this_week, and last_award_date fields
                    teacher_account = Account.query.filter_by(user_id=current_user.id).first()
                    teacher_account.points_awarded += points
                    current_user.points_awarded_this_week += points
                    current_user.last_award_date = datetime.utcnow().date()  # Update last_award_date
                    db.session.commit()

                    # Add a new transaction to the Transactions table in the database
                    transaction = Transactions(
                        sequence=1,
                        from_account_id=current_user.id,
                        dateTime=datetime.utcnow(),
                        to_account_id=student.id,
                        amount=points
                    )
                    db.session.add(transaction)
                    db.session.commit()

                    # Display a success message and redirect the user to the 'award_points' page
                    flash('Transaction successful!', 'success')
                    return redirect(url_for('auth.award_points'))
                
                else:
                    flash('Invalid student ID', 'danger')
            else:
                flash('Invalid student name or class name', 'danger')

        # Retrieve the remaining points and remaining point percentage for the current user
        remaining_points = current_user.remaining_points
        remaining_point_percentage = current_user.remaining_point_percentage

        # Render the 'award_points.html' template with the year groups, classes, students, user, remaining_points, and remaining_point_percentage variables
        return render_template('award_points.html', year_groups=year_groups, classes=classes, students=students, user=current_user, remaining_points=remaining_points, remaining_point_percentage=remaining_point_percentage)
    else:
        return "You are not authorized to access this page."




# Define the route for creating a class
@auth.route('/create_class', methods=['GET', 'POST'])
@login_required
def create_class():
    # Check if the current user has the role of 'teacher'
    if current_user.role.name != 'teacher':
        # If not, display an error message and redirect to the home page
        flash('You must be a teacher to create a class', category='error')
        return redirect(url_for('views.home'))

    # Get a list of all the subjects
    subjects = Subject.query.all()

    # Check if the request method is POST
    if request.method == 'POST':
        # Get the selected subject and year group from the form
        subject_id = request.form.get('subject')
        year_group = request.form.get('year_group')

        # Check if a class with the same subject, year group, and teacher already exists
        existing_class = Class.query.filter_by(subject_id=subject_id, year_group=year_group, teacher_id=current_user.id).first()
        if existing_class:
            # If a class already exists, display the existing class and redirect to the create_class page
            return render_template('create_class.html', existing_class=existing_class, user=current_user, subjects=subjects)

        # If a class does not already exist, create a new class
        if subject_id and year_group:
            # Get the subject object from the subject ID
            subject = Subject.query.get(subject_id)

            # Create a base class name using the year group, subject name, and teacher's initials
            base_class_name = f"{year_group}{subject.name[0]}{current_user.first_name[0]}{current_user.last_name[0]}"
            class_name = base_class_name
            counter = 1

            # Check if a class with the same name already exists
            while Class.query.filter_by(name=class_name).first() is not None:
                # If a class with the same name exists, append a counter to the name and check again
                class_name = base_class_name + str(counter)
                counter += 1

            # Create a new class with the generated name, subject ID, year group, and teacher ID
            new_class = Class(name=class_name, subject_id=subject_id, year_group=year_group, teacher_id=current_user.id)
            db.session.add(new_class)
            db.session.commit()

            # Display a success message
            flash('Class created successfully', category='success')
        else:
            # If the subject or year group is not provided, display an error message
            flash('Please fill out all fields', category='error')

    # Render the create_class page with the current user and subjects
    return render_template("create_class.html", user=current_user, subjects=subjects)

#//teacher--------------------------------------------------------------------------------------------------------------------------------------------------------------------------



#//student--------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# define a route decorator for /student/<int:student_id>
@auth.route('/student/<int:student_id>')
@login_required
def student(student_id):
    # Get the student object by the current user's id and role
    student = User.query.filter_by(id=current_user.id, role_id=3).first()

    # If the current user is a student
    if student:
        # Get filters from the request arguments
        search_year_group = request.args.get('year_group', type=int)
        search_subject_id = request.args.get('subject_id', type=int)
        search_teacher_id = request.args.get('teacher_id', type=int)  # New filter
        
        # Create an empty list for search filters
        search_filters = []

        # Add search filters based on request arguments
        if search_year_group:
            search_filters.append(Class.year_group == search_year_group)
        if search_subject_id:
            search_filters.append(Class.subject_id == search_subject_id)
        if search_teacher_id:  # Add the filter for teacher_id
            search_filters.append(Class.teacher_id == search_teacher_id)
        
        # If there are search filters, filter the classes using AND operator
        if search_filters:
            classes = Class.query.filter(and_(*search_filters)).all()
        # Else fetch all classes
        else:
            classes = Class.query.all()
        
        # Fetch all subjects, teachers and join requests for the student
        subjects = Subject.query.all()
        teachers = User.query.filter_by(role_id=2).all()
        join_requests = JoinRequest.query.filter_by(student_id=student_id).all()
        
        # Render the student.html template with the required data
        return render_template('student.html', student=student, classes=classes, user=current_user, search_year_group=search_year_group, search_subject_id=search_subject_id, search_teacher_id=search_teacher_id, subjects=subjects, teachers=teachers)

    # If the current user is not a student
    else:
        # Flash a message and redirect to the home page
        flash('You are not a student!', category='error')
        return redirect(url_for('views.home'))


# define a route decorator for /request_join_class/<int:student_id>/<int:class_id> with the GET method
@auth.route('/request_join_class/<int:student_id>/<int:class_id>', methods=['GET'])
def request_join_class(student_id, class_id):
    # Check if the user already has a join request for the class
    existing_join_request = JoinRequest.query.filter_by(student_id=student_id, class_id=class_id).first()

    # If the user already has a join request for the class
    if existing_join_request:
        # Flash a message and redirect to the student page
        flash('You already have a join request for this class.', 'warning')
        return redirect(url_for('auth.student', student_id=student_id))

    # Create a new join request object
    join_request = JoinRequest(student_id=student_id, class_id=class_id, status='pending')

    # Add the join request to the database and commit changes
    db.session.add(join_request)
    db.session.commit()

    # Flash a message and redirect to the student page
    flash('Join request sent successfully', category='success')
    return redirect(url_for('auth.student', student_id=student_id))



# Define a route for displaying available items and allowing students to purchase items
@auth.route('/student_rewards', methods=['GET', 'POST'])
@login_required  # Only allow authenticated users to access this route
def student_rewards():
    # Retrieve the current user's information
    student = User.query.filter_by(id=current_user.id, role_id=3).first()
    
    # If the user is a student, display the available items and process the purchase if the form is submitted
    if student:
        available_items = [
            {'name': 'Pen', 'description': 'A high-quality pen', 'points': 10},
            {'name': 'Notebook', 'description': 'A durable notebook', 'points': 20},
            {'name': 'Coffee', 'description': 'A delicious cup of coffee', 'points': 30},
            {'name': 'Lunch', 'description': 'A nutritious lunch', 'points': 50},
        ]
        
        # Check if the form is submitted via POST request
        if request.method == 'POST':
            item_index = int(request.form.get('item_index'))
            item = available_items[item_index]
            student_account = student.account  # Retrieve the student's account information
            
            # Check if the student has enough points to purchase the item
            if student_account.balance >= item['points']:
                # Deduct points from the student's account
                student_account.balance -= item['points']
                db.session.commit()

                # Generate a unique coupon code and create a coupon object to add to the database
                coupon_code = None  # TODO: Generate unique 8-digit code
                coupon = Coupon(student_id=student.id, name=item['name'], description=item['description'], points_cost=item['points'], code=coupon_code, redeemed=False, redeem_date=None)
                db.session.add(coupon)
                db.session.commit()
                
                # Create a transaction object to track the purchase in the database
                transaction = Transactions(sequence=1, from_account_id=student_account.id, dateTime=datetime.utcnow(), to_account_id=None, amount=-item['points'], account_id=student_account.id, code=coupon_code)
                db.session.add(transaction)
                db.session.commit()
                
                # Display a success message to the user
                flash('Coupon purchased successfully!', 'success')
            
            # If the student does not have enough points, display an error message
            else:
                flash('You do not have enough points to purchase this item', 'error')
        
        # Render the template with the available items and the student's information
        return render_template('student_rewards.html', available_items=available_items, student=student, user=current_user)
    
    # If the user is not a student, display an error message and redirect to the home page
    else:
        flash('You are not a student!', category='error')
        return redirect(url_for('views.home'))

# Define a route for displaying the student dashboard
@auth.route('/dashboard')
@login_required  # Only allow authenticated users to access this route
def dashboard():
    # Retrieve the current user's information and account details
    user = current_user
    account = user.account
    balance = account.balance
    transactions = account.transactions
    
    # Render the template with the account balance and transaction history
    return render_template('student_dashboard.html', balance=balance, transactions=transactions, user=current_user)


# Create a new route for redeeming a coupon, which is accessed via a POST request
@auth.route('/redeem_coupon', methods=['POST'])

# Use the login_required decorator to require authentication before the function can be called
@login_required
def redeem_coupon():
    # Retrieve the coupon_id from the POST request's form data
    coupon_id = request.form.get('coupon_id')

    # Print a message indicating that a redeem_coupon request has been received for the given coupon ID
    print("Received redeem_coupon request for coupon ID:", coupon_id)

    # Get the Coupon object with the given ID from the database
    coupon = Coupon.query.get(coupon_id)

    # Check if the coupon exists and has not been redeemed yet
    if coupon and not coupon.redeemed:
        # Generate a code for the coupon and mark it as redeemed
        coupon.code = coupon.generate_code()
        coupon.redeem()

        # Find the transaction record associated with the coupon and update its redeem date
        transaction = Transactions.query.filter_by(coupon_id=coupon_id).first()
        if transaction:
            transaction.date_redeemed = datetime.utcnow()

        # Commit the changes to the database
        db.session.commit()

        # Print a message indicating that the coupon has been updated with a new code and redeem date
        print("Coupon updated with code and redeem date:", coupon.code)

        # Return a JSON response with the new coupon code and a success flag
        return jsonify({'code': coupon.code, 'success': True})
    else:
        # If the coupon does not exist or has already been redeemed, return a JSON response with an error message and a failure flag
        print("Failed to redeem coupon")
        return jsonify({'message': 'Failed to redeem coupon', 'success': False})



#//student--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
