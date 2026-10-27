from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import User, Course, Enrollment, Assignment, Submission, Grade, Activity, Quiz, Exam, Certificate, DiscussionTopic, Notification

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in with administrator credentials first.', 'danger')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        admin_user = User.query.filter_by(username=username, role='admin').first()

        # يدعم التحقق سواء كانت كلمة المرور مشفرة أو نص عادي
        is_valid = False
        if admin_user:
            if hasattr(admin_user, 'check_password'):
                is_valid = admin_user.check_password(password)
            else:
                is_valid = (admin_user.password == password)

        if admin_user and is_valid:
            session['admin_id'] = admin_user.id
            session['admin_logged_in'] = True
            flash('Welcome back, Admin!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid admin credentials. Access restricted.', 'danger')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.pop('admin_id', None)
    session.pop('admin_logged_in', None)
    flash('You have logged out from the admin console.', 'success')
    return redirect(url_for('admin.login'))


def _duplicate_profile_id(field_name, value, exclude_id=None):
    if not value:
        return None
    query = User.query.filter(getattr(User, field_name) == value)
    if exclude_id:
        query = query.filter(User.id != exclude_id)
    return query.first()


def _apply_student_profile(user, form):
    user.name_person = form.get('name_person', '').strip()
    user.university_id = form.get('university_id', '').strip() or None
    user.phone = form.get('phone', '').strip() or None
    user.department = form.get('department', '').strip() or None
    user.level = form.get('level', '').strip() or None
    user.gender = form.get('gender', '').strip() or None
    user.status = form.get('status', 'Active').strip() or 'Active'


def _apply_teacher_profile(user, form):
    user.name_person = form.get('name_person', '').strip()
    user.employee_id = form.get('employee_id', '').strip() or None
    user.phone = form.get('phone', '').strip() or None
    user.department = form.get('department', '').strip() or None
    user.office_number = form.get('office_number', '').strip() or None
    user.academic_rank = form.get('academic_rank', '').strip() or None
    user.gender = form.get('gender', '').strip() or None
    user.status = form.get('status', 'Active').strip() or 'Active'


def _duplicate_user(username, email, exclude_id=None):
    q1 = User.query.filter_by(username=username)
    q2 = User.query.filter_by(email=email)
    if exclude_id:
        q1 = q1.filter(User.id != exclude_id)
        q2 = q2.filter(User.id != exclude_id)
    return q1.first(), q2.first()


@admin_bp.route('/')
@admin_required
def dashboard():
    stats = {
        'students': User.query.filter_by(role='student').count(),
        'teachers': User.query.filter_by(role='teacher').count(),
        'courses': Course.query.count(),
        'enrollments': Enrollment.query.count(),
        'assignments': Assignment.query.count(),
        'quizzes': Quiz.query.count(),
        'exams': Exam.query.count(),
        'certificates': Certificate.query.count(),
        'topics': DiscussionTopic.query.count(),
    }
    return render_template('admin/dashboard.html', stats=stats)


@admin_bp.route('/students')
@admin_required
def manage_students():
    return render_template('admin/manage_students.html', students=User.query.filter_by(role='student').all())


@admin_bp.route('/students/add', methods=['GET', 'POST'])
@admin_required
def add_student():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        university_id = request.form.get('university_id', '').strip()
        if not all([request.form.get('name_person','').strip(), university_id, username, email, password]):
            flash('Please complete all required fields.', 'danger')
            return render_template('admin/add_student.html')
        duplicate_username, duplicate_email = _duplicate_user(username, email)
        if duplicate_username or duplicate_email:
            flash('Username or email is already registered.', 'danger')
            return render_template('admin/add_student.html')
        if _duplicate_profile_id('university_id', university_id):
            flash('University ID is already registered.', 'danger')
            return render_template('admin/add_student.html')
        student = User(username=username, email=email, role='student')
        _apply_student_profile(student, request.form)
        student.set_password(password)
        student.visible_password = password
        try:
            db.session.add(student)
            db.session.commit()
            flash('Student account created successfully.', 'success')
            return redirect(url_for('admin.manage_students'))
        except IntegrityError:
            db.session.rollback()
            flash('A student with the same username, email, or university ID already exists.', 'danger')
    return render_template('admin/add_student.html')


@admin_bp.route('/students/delete/<int:student_id>', methods=['POST'])
@admin_required
def delete_student(student_id):
    student = User.query.get_or_404(student_id)
    if student.role != 'student':
        flash('The selected account is not a student.', 'danger')
        return redirect(url_for('admin.manage_students'))
    try:
        Activity.query.filter_by(student_id=student.id).delete(synchronize_session=False)
        db.session.delete(student)
        db.session.commit()
        flash('Student and related records deleted successfully.', 'success')
    except Exception:
        db.session.rollback()
        flash('Student could not be deleted because related data still exists.', 'danger')
    return redirect(url_for('admin.manage_students'))


@admin_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_student(student_id):
    student = User.query.get_or_404(student_id)
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip().lower()
        university_id = request.form.get('university_id','').strip()
        du, de = _duplicate_user(username, email, student.id)
        if du or de:
            flash('Username or email is already used by another account.', 'danger')
            return render_template('admin/edit_student.html', student=student)
        if _duplicate_profile_id('university_id', university_id, student.id):
            flash('University ID is already used by another student.', 'danger')
            return render_template('admin/edit_student.html', student=student)
        student.username, student.email = username, email
        _apply_student_profile(student, request.form)
        password = request.form.get('password','')
        if password:
            student.set_password(password)
            student.visible_password = password
        db.session.commit()
        flash('Student profile updated successfully.', 'success')
        return redirect(url_for('admin.manage_students'))
    return render_template('admin/edit_student.html', student=student)


@admin_bp.route('/students/<int:student_id>/reset-password', methods=['GET','POST'])
@admin_required
def reset_student_password(student_id):
    return _reset_password(student_id, 'student', 'admin.manage_students')


def _reset_password(user_id, role, redirect_endpoint):
    user = User.query.get_or_404(user_id)
    if user.role != role:
        flash('Invalid account type.', 'danger')
        return redirect(url_for(redirect_endpoint))
    if request.method == 'POST':
        password = request.form.get('new_password','')
        confirm = request.form.get('confirm_password','')
        if len(password) < 6:
            flash('Password must contain at least 6 characters.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            user.set_password(password)
            user.visible_password = password
            db.session.commit()
            flash('Password reset successfully.', 'success')
            return redirect(url_for(redirect_endpoint))
    return render_template('admin/reset_password.html', user=user)


@admin_bp.route('/students/<int:student_id>/enroll', methods=['GET', 'POST'])
@admin_required
def enroll_courses(student_id):
    student = User.query.get_or_404(student_id)
    courses = Course.query.all()
    if request.method == 'POST':
        ids = request.form.getlist('course_ids')
        if not ids:
            flash('Please select at least one course.', 'warning')
        else:
            for cid in ids:
                if not Enrollment.query.filter_by(student_id=student.id, course_id=int(cid)).first():
                    db.session.add(Enrollment(student_id=student.id, course_id=int(cid)))
            db.session.commit()
            flash('Courses enrolled successfully!', 'success')
            return redirect(url_for('admin.manage_students'))
    return render_template('admin/enroll_courses.html', student=student, courses=courses)


@admin_bp.route('/teachers')
@admin_required
def manage_teachers():
    return render_template('admin/manage_teachers.html', teachers=User.query.filter_by(role='teacher').all())


@admin_bp.route('/teachers/add', methods=['GET','POST'])
@admin_required
def add_teacher():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        employee_id = request.form.get('employee_id','').strip()
        du, de = _duplicate_user(username, email)
        if not all([request.form.get('name_person','').strip(), employee_id, username, email, password]):
            flash('Please complete all required fields.', 'danger')
        elif du or de:
            flash('Username or email is already registered.', 'danger')
        elif _duplicate_profile_id('employee_id', employee_id):
            flash('Employee ID is already registered.', 'danger')
        else:
            teacher = User(username=username, email=email, role='teacher')
            _apply_teacher_profile(teacher, request.form)
            teacher.set_password(password)
            teacher.visible_password = password
            db.session.add(teacher)
            db.session.commit()
            flash('Instructor account created successfully.','success')
            return redirect(url_for('admin.manage_teachers'))
    return render_template('admin/add_teacher.html')


@admin_bp.route('/teachers/delete/<int:teacher_id>', methods=['POST'])
@admin_required
def delete_teacher(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    if teacher.courses:
        flash('Reassign or delete this teacher’s courses before deleting the account.', 'warning')
    else:
        db.session.delete(teacher)
        db.session.commit()
        flash('Teacher deleted successfully!','success')
    return redirect(url_for('admin.manage_teachers'))


@admin_bp.route('/teachers/<int:teacher_id>/edit', methods=['GET','POST'])
@admin_required
def edit_teacher(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip().lower()
        employee_id = request.form.get('employee_id','').strip()
        du, de = _duplicate_user(username, email, teacher.id)
        if du or de:
            flash('Username or email is already used by another account.','danger')
            return render_template('admin/edit_teacher.html',teacher=teacher)
        if _duplicate_profile_id('employee_id', employee_id, teacher.id):
            flash('Employee ID is already used by another instructor.','danger')
            return render_template('admin/edit_teacher.html',teacher=teacher)
        teacher.username, teacher.email = username, email
        _apply_teacher_profile(teacher, request.form)
        password = request.form.get('password','')
        if password:
            teacher.set_password(password)
            teacher.visible_password = password
        db.session.commit()
        flash('Instructor profile updated successfully.','success')
        return redirect(url_for('admin.manage_teachers'))
    return render_template('admin/edit_teacher.html',teacher=teacher)


@admin_bp.route('/teachers/<int:teacher_id>/reset-password', methods=['GET','POST'])
@admin_required
def reset_teacher_password(teacher_id):
    return _reset_password(teacher_id, 'teacher', 'admin.manage_teachers')


@admin_bp.route('/teachers/<int:teacher_id>/assign_courses', methods=['GET','POST'])
@admin_required
def assign_courses(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    courses = Course.query.all()
    if request.method == 'POST':
        course = Course.query.get_or_404(int(request.form['course_id']))
        course.teacher_id = teacher.id
        db.session.commit()
        flash('Course assigned to teacher!','success')
        return redirect(url_for('admin.manage_teachers'))
    return render_template('admin/assign_courses.html',teacher=teacher,courses=courses)


@admin_bp.route('/courses')
@admin_required
def manage_courses():
    return render_template('admin/manage_courses.html',courses=Course.query.all())


@admin_bp.route('/courses/add', methods=['GET','POST'])
@admin_required
def add_course():
    teachers = User.query.filter_by(role='teacher').all()
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        if not teacher_id:
            flash('Please select a teacher.','danger')
            return render_template('admin/add_course.html',teachers=teachers)
        course = Course(code=request.form['code'].strip(),name=request.form['name'].strip(),description=request.form.get('description',''),teacher_id=int(teacher_id),course_identifier=request.form.get('course_identifier','').strip())
        try:
            db.session.add(course)
            db.session.commit()
            flash('Course added successfully!','success')
            return redirect(url_for('admin.manage_courses'))
        except IntegrityError:
            db.session.rollback()
            flash('Course code or identifier already exists.','danger')
    return render_template('admin/add_course.html',teachers=teachers)


@admin_bp.route('/courses/delete/<int:course_id>', methods=['POST'])
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    try:
        Activity.query.filter_by(course_id=course.id).delete(synchronize_session=False)
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully!','success')
    except Exception:
        db.session.rollback()
        flash('Course could not be deleted because related data still exists.','danger')
    return redirect(url_for('admin.manage_courses'))


@admin_bp.route('/courses/<int:course_id>/edit', methods=['GET','POST'])
@admin_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    teachers = User.query.filter_by(role='teacher').all()
    if request.method == 'POST':
        course.code = request.form['code'].strip()
        course.name = request.form['name'].strip()
        course.description = request.form.get('description','')
        teacher_id = request.form.get('teacher_id')
        course.teacher_id = int(teacher_id) if teacher_id else course.teacher_id
        db.session.commit()
        flash('Course updated successfully!','success')
        return redirect(url_for('admin.manage_courses'))
    return render_template('admin/edit_course.html',course=course,teachers=teachers)


@admin_bp.route('/courses/<int:course_id>/assign', methods=['GET','POST'])
@admin_required
def assign_course(course_id):
    course = Course.query.get_or_404(course_id)
    teachers = User.query.filter_by(role='teacher').all()
    if request.method == 'POST':
        course.teacher_id = int(request.form['teacher_id'])
        db.session.commit()
        flash('Teacher assigned successfully!','success')
        return redirect(url_for('admin.manage_courses'))
    return render_template('admin/assign_course.html',course=course,teachers=teachers)


@admin_bp.route('/reports')
@admin_required
def reports_teachers():
    report_data = []
    for teacher in User.query.filter_by(role='teacher').all():
        courses_data = []
        for course in teacher.courses:
            students_data = []
            for enrollment in course.enrollments:
                student = enrollment.student
                subs = []
                for assignment in course.assignments:
                    submission = Submission.query.filter_by(student_id=student.id,assignment_id=assignment.id).first()
                    subs.append({'assignment_title':assignment.title,'grade':submission.grade if submission else 'Not graded'})
                students_data.append({'student':student,'submissions':subs})
            courses_data.append({'course':course,'student_count':len(course.enrollments),'assignments':course.assignments,'students_data':students_data})
        report_data.append({'teacher':teacher,'courses':courses_data})
    return render_template('admin/reports.html',report_data=report_data)


@admin_bp.route('/courses/<int:course_id>/students')
@admin_required
def course_students(course_id):
    course = Course.query.get_or_404(course_id)
    data = []
    for enrollment in course.enrollments:
        student = enrollment.student
        total = sum(s.grade for s in student.submissions if s.assignment.course_id==course.id and s.grade is not None)
        data.append({'student':student,'total_grade':total})
    return render_template('admin/course_students.html',course=course,student_data=data)


@admin_bp.route('/certificates')
@admin_required
def certificates():
    items = Certificate.query.order_by(Certificate.issued_at.desc()).all()
    return render_template('admin/certificates.html', certificates=items)


@admin_bp.route('/certificates/<int:certificate_id>')
@admin_required
def view_certificate(certificate_id):
    certificate = Certificate.query.get_or_404(certificate_id)
    return render_template('student/certificate.html', student=certificate.student, course=certificate.course,
                           teacher=certificate.course.teacher, percentage=certificate.final_grade,
                           certificate=certificate, today=certificate.issued_at)


@admin_bp.app_context_processor
def admin_header_counts():
    return {
        'admin_unread_count': Notification.query.filter_by(is_read=False).count(),
        'admin_message_count': DiscussionTopic.query.count(),
    }


@admin_bp.route('/notifications')
@admin_required
def notifications():
    items = Notification.query.order_by(Notification.created_at.desc()).limit(100).all()
    return render_template('admin/notifications.html', notifications=items)


@admin_bp.route('/notifications/read-all', methods=['POST'])
@admin_required
def clear_notifications():
    Notification.query.update({'is_read': True}, synchronize_session=False)
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('admin.notifications'))


@admin_bp.route('/messages')
@admin_required
def messages():
    topics = DiscussionTopic.query.order_by(DiscussionTopic.updated_at.desc()).limit(50).all()
    return render_template('admin/messages.html', topics=topics)


@admin_bp.route('/settings')
@admin_required
def settings():
    return render_template('admin/settings.html')


@admin_bp.route('/help')
@admin_required
def help_center():
    return render_template('admin/help.html')
