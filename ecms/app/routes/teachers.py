from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from flask_login import login_required, current_user, login_user, logout_user
from app.models import (
    User, Course, Unit, Assignment, Quiz, QuizQuestion, 
    Exam, Grade, Activity, Notification, Certificate,
    ExamQuestion, Enrollment, Submission
)
from PIL import Image, ImageDraw, ImageFont
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
from sqlalchemy.orm import joinedload
from app import db, login_manager
from app.services import notify_course_students, course_progress, final_grade, issue_certificate
import os
import uuid

try:
    from app.models import StudentActivity
except ImportError:
    StudentActivity = None

teachers_bp = Blueprint("teachers", __name__, url_prefix="/teacher")

# Upload configuration safe for Vercel Serverless
if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'uploads'))

ALLOWED_EXTENSIONS = {'pdf','doc','docx','ppt','pptx','xls','xlsx','txt','jpg','jpeg','png','zip'}
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception:
    pass


def allowed_file(filename):
    if not filename:
        return False
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _parse_datetime(value, label):
    if not value:
        raise ValueError(f"{label} is required.")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {label.lower()}.") from exc


def _question_numbers(form):
    numbers = []
    for key in form.keys():
        if key.startswith("question_"):
            suffix = key.removeprefix("question_")
            if suffix.isdigit():
                numbers.append(int(suffix))
    return sorted(set(numbers))


def _question_payload(form, number):
    text = (form.get(f"question_{number}") or "").strip()
    question_type = (form.get(f"type_{number}") or "short_answer").strip()
    options = (form.get(f"options_{number}") or "").strip()
    answer = (form.get(f"answer_{number}") or "").strip()

    try:
        score = float(form.get(f"score_{number}") or 1)
    except ValueError as exc:
        raise ValueError(f"Question {number} has an invalid score.") from exc

    if not text:
        raise ValueError(f"Question {number} text is required.")
    if score <= 0:
        raise ValueError(f"Question {number} score must be greater than zero.")

    allowed_types = {"mcq", "true_false", "short_answer", "essay"}
    if question_type not in allowed_types:
        raise ValueError(f"Question {number} has an unsupported type.")

    if question_type == "mcq":
        choices = [item.strip() for item in options.split(",") if item.strip()]
        if len(choices) < 2:
            raise ValueError(f"Question {number} needs at least two choices.")
        if not answer:
            raise ValueError(f"Question {number} needs a correct answer.")
        if answer not in choices:
            raise ValueError(f"Question {number} correct answer must match one listed choice.")
        options = ",".join(choices)
    elif question_type == "true_false":
        options = "True,False"
        normalized = answer.lower()
        if normalized not in {"true", "false"}:
            raise ValueError(f"Question {number} answer must be True or False.")
        answer = "True" if normalized == "true" else "False"
    elif question_type == "short_answer" and not answer:
        raise ValueError(f"Question {number} needs a correct answer.")
    elif question_type == "essay":
        answer = answer or "Manual grading required"
        options = ""

    return {
        "question_text": text,
        "question_type": question_type,
        "options": options,
        "answer": answer,
        "score": score,
    }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def _teacher_nav_context(teacher):
    ungraded = Submission.query.join(Assignment).join(Course).filter(Course.teacher_id == teacher.id, Submission.grade.is_(None)).count()
    unread = Notification.query.filter_by(user_id=teacher.id, is_read=False).count()
    return {'nav_ungraded': ungraded, 'nav_notifications': unread}


# ------------------------- Authentication -------------------------
@teachers_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated and getattr(current_user, 'role', '').lower() == "teacher":
        return redirect(url_for("teachers.dashboard", teacher_id=current_user.id))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if (email in ["instructor@learnova.edu", "demo_instructor", "teacher@learnova.edu", "demo@learnova.edu"]) and password == "demo123":
            try:
                db.session.rollback()
                demo_teacher = User.query.filter(User.role.ilike("teacher")).first()
                if demo_teacher:
                    session['is_demo'] = True
                    login_user(demo_teacher)
                    
                    # تسجيل إشعار دخول
                    db.session.add(Notification(
                        user_id=demo_teacher.id,
                        title="Instructor Login Session",
                        message=f"Logged in successfully via Demo Account on {datetime.now().strftime('%d %b %Y, %I:%M %p')}.",
                        link=f"/teacher/{demo_teacher.id}/dashboard",
                        is_read=False,
                        created_at=datetime.now(timezone.utc)
                    ))
                    db.session.commit()
                    
                    flash("Signed in successfully with Demo Instructor Account.", "success")
                    return redirect(url_for("teachers.dashboard", teacher_id=demo_teacher.id))
            except Exception:
                db.session.rollback()

        session.pop('is_demo', None)
        try:
            user = User.query.filter((User.email == email) | (User.username == email)).first()
            is_valid = False
            if user:
                if hasattr(user, "check_password"):
                    is_valid = user.check_password(password)
                else:
                    is_valid = (user.password == password)

            if user and is_valid and getattr(user, 'role', '').lower() == "teacher":
                login_user(user)
                
                # تسجيل إشعار دخول نظامي
                try:
                    db.session.add(Notification(
                        user_id=user.id,
                        title="Instructor Login Session",
                        message=f"Successful sign-in detected on {datetime.now().strftime('%d %b %Y, %I:%M %p')}.",
                        link=f"/teacher/{user.id}/dashboard",
                        is_read=False,
                        created_at=datetime.now(timezone.utc)
                    ))
                    db.session.commit()
                except Exception:
                    db.session.rollback()

                return redirect(url_for("teachers.dashboard", teacher_id=user.id))
        except Exception:
            db.session.rollback()

        flash("Invalid credentials or not authorized as an instructor.", "danger")
    return render_template("teacher/login.html")


@teachers_bp.route("/logout")
@login_required
def logout():
    session.pop('is_demo', None)
    logout_user()
    return redirect(url_for("teachers.login"))


# ------------------------- Dashboard -------------------------
@teachers_bp.route("/<int:teacher_id>/dashboard")
@login_required
def dashboard(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    if current_user.id != teacher.id or current_user.role != 'teacher':
        flash('Access denied.', 'danger')
        return redirect(url_for('teachers.login'))

    courses = Course.query.filter_by(teacher_id=teacher.id).all()
    student_ids = {e.student_id for c in courses for e in getattr(c, 'enrollments', [])}
    assignment_count = sum(len(getattr(c, 'assignments', [])) for c in courses)
    quiz_count = sum(len(getattr(c, 'quizzes', [])) for c in courses)
    ungraded = Submission.query.join(Assignment).join(Course).filter(Course.teacher_id == teacher.id, Submission.grade.is_(None)).count()
    upcoming = sorted([a for c in courses for a in getattr(c, 'assignments', []) if a.due_date and a.due_date >= datetime.now()], key=lambda a: a.due_date)[:5]
    stats = {'courses': len(courses), 'students': len(student_ids), 'assignments': assignment_count, 'quizzes': quiz_count, 'ungraded': ungraded}
    return render_template("teacher/dashboard.html", teacher=teacher, courses=courses, stats=stats, upcoming=upcoming, **_teacher_nav_context(teacher))


# ------------------------- Courses List -------------------------
@teachers_bp.route("/<int:teacher_id>/courses")
@login_required
def courses(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    if current_user.id != teacher.id or current_user.role != 'teacher':
        flash('Access denied.', 'danger')
        return redirect(url_for('teachers.login'))
    courses = Course.query.filter_by(teacher_id=teacher.id).all()
    student_ids = {e.student_id for c in courses for e in c.enrollments}
    stats = {'students': len(student_ids), 'assignments': sum(len(c.assignments) for c in courses), 'quizzes': sum(len(c.quizzes) for c in courses)}
    return render_template("teacher/courses.html", teacher=teacher, courses=courses, stats=stats, **_teacher_nav_context(teacher))


# ------------------------- Students List -------------------------
@teachers_bp.route("/<int:teacher_id>/students")
@login_required
def students(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    enrolled_students = set()
    for course in teacher.courses:
        for enrollment in course.enrollments:
            enrolled_students.add(enrollment.student)

    return render_template("teacher/students.html", teacher=teacher, students=list(enrolled_students), **_teacher_nav_context(teacher))


# ------------------------- Assignments List -------------------------
@teachers_bp.route("/<int:teacher_id>/assignments")
@login_required
def assignments(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    items = Assignment.query.join(Course).filter(Course.teacher_id == teacher.id).all()
    return render_template("teacher/assignments.html", teacher=teacher, assignments=items, **_teacher_nav_context(teacher))


# ------------------------- View Course -------------------------
@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>")
@login_required
def view_course(teacher_id, course_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.options(
        joinedload(Course.units),
        joinedload(Course.assignments),
        joinedload(Course.quizzes).joinedload(Quiz.questions),
        joinedload(Course.exams).joinedload(Exam.questions),
        joinedload(Course.enrollments).joinedload(Enrollment.student)
    ).get_or_404(course_id)

    return render_template(
        "teacher/view_course.html",
        teacher=teacher,
        course=course,
        units=course.units,
        assignments=course.assignments,
        quizzes=course.quizzes,
        exams=course.exams,
        students=[enrollment.student for enrollment in course.enrollments]
    )


# ------------------------- Add Unit -------------------------
@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/add_unit", methods=["GET", "POST"])
@login_required
def add_unit(teacher_id, course_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.get_or_404(course_id)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        file = request.files.get("file")

        if not title:
            flash("Unit title is required.", "danger")
            return render_template("teacher/add_unit.html", teacher=teacher, course=course, course_id=course_id)

        filename = None
        if file and file.filename and file.filename.strip() != '':
            if allowed_file(file.filename):
                try:
                    original = secure_filename(file.filename)
                    filename = f'{uuid.uuid4().hex}_{original}'
                    upload_target = '/tmp/uploads' if os.environ.get('VERCEL') else UPLOAD_FOLDER
                    os.makedirs(upload_target, exist_ok=True)
                    file.save(os.path.join(upload_target, filename))
                except Exception:
                    filename = None

        try:
            unit = Unit(title=title, file_path=filename, course_id=course_id)
            db.session.add(unit)
            db.session.commit()
            flash("Unit added successfully.", "success")

            try:
                notify_course_students(course, 'New learning unit', f'A new unit “{title}” was added to {course.name}.', f'/student/courses/{course.id}')
                db.session.commit()
            except Exception:
                db.session.rollback()

            return redirect(url_for("teachers.view_course", teacher_id=teacher_id, course_id=course_id))

        except Exception as exc:
            db.session.rollback()
            flash(f"Could not add unit: {exc}", "danger")
            return render_template("teacher/add_unit.html", teacher=teacher, course=course, course_id=course_id)

    return render_template("teacher/add_unit.html", teacher=teacher, course=course, course_id=course_id)


# ------------------------- Add Assignment -------------------------
@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/add_assignment", methods=["GET", "POST"])
@login_required
def add_assignment(teacher_id, course_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.get_or_404(course_id)

    if current_user.id != teacher.id and current_user.role.lower() != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("teachers.dashboard", teacher_id=current_user.id))

    if course.teacher_id != teacher.id and current_user.role.lower() != "admin":
        flash("You do not have permission to modify this course.", "danger")
        return redirect(url_for("teachers.courses", teacher_id=teacher.id))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        assignment_type = (request.form.get("assignment_type") or "homework").strip()

        if assignment_type not in {"homework", "project"}:
            flash("Please use the Quiz Builder to create quizzes.", "warning")
            return redirect(url_for("teachers.add_quiz", teacher_id=teacher.id, course_id=course.id))

        if not title:
            flash("Assignment title is required.", "danger")
            return render_template("teacher/add_assignment.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))

        try:
            start_date = _parse_datetime(request.form.get("start_date"), "Start date")
            due_date = _parse_datetime(request.form.get("due_date"), "Due date")
            if due_date <= start_date:
                raise ValueError("Due date must be after the start date.")
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("teacher/add_assignment.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))

        assignment_file = request.files.get("assignment_file")
        if assignment_file and assignment_file.filename and not allowed_file(assignment_file.filename):
            flash("Unsupported assignment file type.", "danger")
            return render_template("teacher/add_assignment.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))

        try:
            assignment = Assignment(
                title=title,
                description=description,
                assignment_type=assignment_type,
                start_date=start_date,
                due_date=due_date,
                course_id=course.id,
            )
            db.session.add(assignment)
            db.session.flush()

            if assignment_file and assignment_file.filename:
                try:
                    original_name = secure_filename(assignment_file.filename)
                    stored_name = f"assignment_{assignment.id}_{uuid.uuid4().hex}_{original_name}"
                    upload_target = '/tmp/uploads' if os.environ.get('VERCEL') else UPLOAD_FOLDER
                    os.makedirs(upload_target, exist_ok=True)
                    assignment_file.save(os.path.join(upload_target, stored_name))
                except Exception:
                    pass

            db.session.commit()
            flash("Assignment created successfully.", "success")

            try:
                notify_course_students(course, "New assignment", f"‘{title}’ was added to {course.name}. Due: {due_date:%d %b %Y %H:%M}.", f"/student/courses/{course.id}")
                db.session.commit()
            except Exception:
                db.session.rollback()

            return redirect(url_for("teachers.view_course", teacher_id=teacher.id, course_id=course.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not create assignment: {exc}", "danger")
            return render_template("teacher/add_assignment.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))

    return render_template("teacher/add_assignment.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))


@teachers_bp.route("/assignments/<int:assignment_id>/attachment")
@login_required
def assignment_attachment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    course = assignment.course

    is_teacher_owner = (current_user.role.lower() == "teacher" and course.teacher_id == current_user.id)
    is_enrolled_student = (current_user.role.lower() == "student" and Enrollment.query.filter_by(student_id=current_user.id, course_id=course.id).first() is not None)
    is_admin = current_user.role.lower() == "admin"

    if not (is_teacher_owner or is_enrolled_student or is_admin):
        flash("Access denied.", "danger")
        return redirect(url_for("teachers.login"))

    prefix = f"assignment_{assignment.id}_"
    matches = []
    if os.path.exists(UPLOAD_FOLDER):
        matches = sorted(filename for filename in os.listdir(UPLOAD_FOLDER) if filename.startswith(prefix))

    if not matches:
        flash("No attachment was uploaded for this assignment.", "warning")
        if current_user.role.lower() == "teacher":
            return redirect(url_for("teachers.view_course", teacher_id=current_user.id, course_id=course.id))
        return redirect(url_for("students.view_course", course_id=course.id))

    return send_from_directory(UPLOAD_FOLDER, matches[-1], as_attachment=True, download_name=matches[-1].split("_", 3)[-1])


# ------------------------- Add Quiz -------------------------
@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/add_quiz", methods=["GET", "POST"])
@login_required
def add_quiz(teacher_id, course_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.get_or_404(course_id)

    if current_user.id != teacher.id and current_user.role.lower() != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("teachers.dashboard", teacher_id=current_user.id))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        if not title:
            flash("Quiz title is required.", "danger")
            return render_template("teacher/add_quiz.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))

        try:
            start_date = _parse_datetime(request.form.get("start_date"), "Start date")
            end_date = _parse_datetime(request.form.get("end_date"), "End date")
            if end_date <= start_date:
                raise ValueError("End date must be after the start date.")
            numbers = _question_numbers(request.form)
            if not numbers:
                raise ValueError("Add at least one quiz question.")
            questions = [_question_payload(request.form, number) for number in numbers]
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("teacher/add_quiz.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))

        try:
            assignment = Assignment(
                title=title,
                description=description,
                assignment_type="quiz",
                start_date=start_date,
                due_date=end_date,
                course_id=course.id,
            )
            db.session.add(assignment)
            db.session.flush()

            quiz = Quiz(
                assignment_id=assignment.id,
                course_id=course.id,
                title=title,
                description=description,
                start_date=start_date,
                end_date=end_date,
            )
            db.session.add(quiz)
            db.session.flush()

            for payload in questions:
                db.session.add(QuizQuestion(quiz_id=quiz.id, **payload))

            db.session.commit()
            flash(f"Quiz created successfully with {len(questions)} questions.", "success")

            try:
                notify_course_students(course, "New quiz", f"‘{title}’ is now available in {course.name}.", f"/student/courses/{course.id}")
                db.session.commit()
            except Exception:
                db.session.rollback()

            return redirect(url_for("teachers.view_course", teacher_id=teacher.id, course_id=course.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error creating quiz: {exc}", "danger")
            return render_template("teacher/add_quiz.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))

    return render_template("teacher/add_quiz.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))


# ------------------------- Add More Quiz Questions -------------------------
@teachers_bp.route("/quiz/<int:quiz_id>/questions", methods=["GET", "POST"])
@login_required
def add_quiz_questions(quiz_id):
    quiz = Quiz.query.options(joinedload(Quiz.questions)).get_or_404(quiz_id)
    course = quiz.course
    teacher = course.teacher

    if current_user.id != teacher.id and current_user.role.lower() != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("teachers.dashboard", teacher_id=current_user.id))

    if request.method == "POST":
        try:
            numbers = _question_numbers(request.form)
            if not numbers:
                raise ValueError("Add at least one question.")
            questions = [_question_payload(request.form, number) for number in numbers]
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("teacher/quiz_questions.html", quiz=quiz, course=course, teacher=teacher, **_teacher_nav_context(teacher))

        try:
            for payload in questions:
                db.session.add(QuizQuestion(quiz_id=quiz.id, **payload))
            db.session.commit()
            flash(f"Added {len(questions)} question(s) successfully.", "success")
            return redirect(url_for("teachers.add_quiz_questions", quiz_id=quiz.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"Failed to add questions: {exc}", "danger")

    return render_template("teacher/quiz_questions.html", quiz=quiz, course=course, teacher=teacher, **_teacher_nav_context(teacher))


@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/add_exam", methods=["GET", "POST"])
@login_required
def add_exam(teacher_id, course_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.get_or_404(course_id)

    if current_user.id != teacher.id and current_user.role.lower() != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("teachers.dashboard", teacher_id=current_user.id))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        if not title:
            flash("Exam title is required.", "danger")
            return render_template("teacher/add_exam.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))

        try:
            start_date = _parse_datetime(request.form.get("start_date"), "Start date")
            end_date = _parse_datetime(request.form.get("end_date"), "End date")
            if end_date <= start_date:
                raise ValueError("End date must be after the start date.")
            numbers = _question_numbers(request.form)
            if not numbers:
                raise ValueError("Add at least one exam question.")
            questions = [_question_payload(request.form, number) for number in numbers]
            calculated_total = sum(item["score"] for item in questions)
            requested_total = float(request.form.get("total_score") or calculated_total)
            total_score = calculated_total if requested_total != calculated_total else requested_total
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("teacher/add_exam.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))

        try:
            exam = Exam(
                title=title,
                description=description,
                total_score=total_score,
                start_date=start_date,
                end_date=end_date,
                course_id=course.id,
            )
            db.session.add(exam)
            db.session.flush()

            for payload in questions:
                db.session.add(ExamQuestion(exam_id=exam.id, **payload))

            db.session.commit()
            flash(f"Exam created successfully with {len(questions)} questions.", "success")

            try:
                notify_course_students(course, "New exam", f"‘{title}’ is now available in {course.name}.", f"/student/courses/{course.id}")
                db.session.commit()
            except Exception:
                db.session.rollback()

            return redirect(url_for("teachers.view_course", teacher_id=teacher.id, course_id=course.id))
        except Exception as exc:
            db.session.rollback()
            flash(f"Failed to create exam: {exc}", "danger")
            return render_template("teacher/add_exam.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))

    return render_template("teacher/add_exam.html", teacher=teacher, course=course, **_teacher_nav_context(teacher))


# ------------------------- Student Details (Modal) -------------------------
@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/students/<int:student_id>/details")
@login_required
def student_details(teacher_id, course_id, student_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.options(
        joinedload(Course.assignments),
        joinedload(Course.quizzes).joinedload(Quiz.questions),
        joinedload(Course.exams),
        joinedload(Course.enrollments),
    ).get_or_404(course_id)
    student = User.query.get_or_404(student_id)

    if current_user.id != teacher.id or current_user.role.lower() != "teacher" or course.teacher_id != teacher.id:
        flash("Access denied.", "danger")
        return redirect(url_for("teachers.login"))

    enrollment = Enrollment.query.filter_by(student_id=student.id, course_id=course.id).first()
    if not enrollment:
        flash("This student is not enrolled in the selected course.", "warning")
        return redirect(url_for("teachers.view_course", teacher_id=teacher.id, course_id=course.id))

    assignments_data = []
    for assignment in course.assignments:
        if assignment.assignment_type == "quiz":
            continue
        submission = Submission.query.filter_by(student_id=student.id, assignment_id=assignment.id).first()
        assignments_data.append({
            "id": assignment.id,
            "title": assignment.title,
            "submitted": submission is not None,
            "score": submission.grade if submission else None,
            "feedback": submission.feedback if submission else None,
            "due_date": assignment.due_date,
        })

    quizzes_data = []
    for quiz in course.quizzes:
        submission = Submission.query.filter_by(student_id=student.id, assignment_id=quiz.assignment_id).order_by(Submission.submitted_at.desc()).first()
        total_possible = sum(float(question.score or 0) for question in quiz.questions) or 1
        quizzes_data.append({
            "id": quiz.id,
            "title": quiz.title,
            "score": submission.grade if submission else None,
            "total": total_possible,
            "completed": submission is not None,
        })

    exams_data = []
    for exam in course.exams:
        grade_row = Grade.query.filter_by(student_id=student.id, exam_id=exam.id).first()
        exams_data.append({
            "id": exam.id,
            "title": exam.title,
            "score": grade_row.score if grade_row else None,
            "total": exam.total_score or 1,
            "completed": grade_row is not None,
        })

    activity_record = Activity.query.filter_by(student_id=student.id, course_id=course.id).first()
    activity_score = activity_record.score if activity_record else 0
    progress = course_progress(student, course)
    overall_grade = final_grade(student, course)

    certificate = Certificate.query.filter_by(student_id=student.id, course_id=course.id).first()

    return render_template(
        "teacher/student_progress.html",
        teacher=teacher,
        course=course,
        student=student,
        assignments=assignments_data,
        quizzes=quizzes_data,
        exams=exams_data,
        activity_score=activity_score,
        progress=progress,
        final_grade=overall_grade,
        certificate=certificate,
        active_page="students",
        **_teacher_nav_context(teacher),
    )


# ------------------------- File Handling -------------------------
@teachers_bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


@teachers_bp.route("/delete_file/<filename>", methods=["POST"])
@login_required
def delete_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash("File deleted successfully.", "success")
    else:
        flash("File not found.", "danger")
    return redirect(request.referrer)


# ------------------------- Update Student Activity -------------------------
@teachers_bp.route("/update_activity/<int:student_id>", methods=["POST"])
@login_required
def update_activity(student_id):
    score = request.form.get("activity_score", type=float)
    if score is None:
        return jsonify({"status": "error", "message": "No score provided"}), 400

    course_id = request.form.get("course_id", type=int)
    if course_id is None:
        return jsonify({"status": "error", "message": "Course ID required"}), 400

    activity = Activity.query.filter_by(student_id=student_id, course_id=course_id).first()
    if not activity:
        activity = Activity(student_id=student_id, course_id=course_id, score=score)
        db.session.add(activity)
    else:
        activity.score = score

    db.session.commit()
    return jsonify({"status": "success", "message": "Activity score updated"})


# ------------------------- Edit Unit -------------------------
@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/units/<int:unit_id>/edit", methods=["GET", "POST"])
@login_required
def edit_unit_page(teacher_id, course_id, unit_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.get_or_404(course_id)
    unit = Unit.query.get_or_404(unit_id)

    if request.method == "POST":
        unit.title = request.form.get("title")
        unit.content = request.form.get("content")

        file = request.files.get("file")
        if file and file.filename and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                upload_target = '/tmp/uploads' if os.environ.get('VERCEL') else UPLOAD_FOLDER
                os.makedirs(upload_target, exist_ok=True)
                file.save(os.path.join(upload_target, filename))
                unit.file_path = filename
            except Exception:
                pass

        db.session.commit()
        flash("Unit updated successfully.", "success")
        return redirect(url_for("teachers.view_course", teacher_id=teacher.id, course_id=course.id))

    return render_template("teacher/edit_unit.html", teacher=teacher, course=course, unit=unit)


@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/assignments/<int:assignment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_assignment_page(teacher_id, course_id, assignment_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.get_or_404(course_id)
    assignment = Assignment.query.get_or_404(assignment_id)

    if current_user.id != teacher.id and current_user.role.lower() != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("teachers.dashboard", teacher_id=current_user.id))

    if course.teacher_id != teacher.id and current_user.role.lower() != "admin":
        flash("You do not have permission to modify this course.", "danger")
        return redirect(url_for("teachers.courses", teacher_id=teacher.id))

    if assignment.course_id != course.id:
        flash("This assignment does not belong to the selected course.", "danger")
        return redirect(url_for("teachers.view_course", teacher_id=teacher.id, course_id=course.id))

    if assignment.assignment_type == "quiz":
        flash("Quiz questions must be edited from the Quiz Questions page.", "warning")
        quiz = Quiz.query.filter_by(assignment_id=assignment.id).first()
        if quiz:
            return redirect(url_for("teachers.add_quiz_questions", quiz_id=quiz.id))

    attachment_prefix = f"assignment_{assignment.id}_"
    current_attachments = []
    if os.path.exists(UPLOAD_FOLDER):
        current_attachments = sorted(filename for filename in os.listdir(UPLOAD_FOLDER) if filename.startswith(attachment_prefix))
    current_attachment = current_attachments[-1] if current_attachments else None
    current_attachment_name = current_attachment.split("_", 3)[-1] if current_attachment else None

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        assignment_type = (request.form.get("assignment_type") or assignment.assignment_type).strip()

        if assignment_type not in {"homework", "project"}:
            flash("Only homework and project types are allowed here.", "danger")
            return render_template("teacher/edit_assignment.html", teacher=teacher, course=course, assignment=assignment, current_attachment=current_attachment, current_attachment_name=current_attachment_name, **_teacher_nav_context(teacher))

        if not title:
            flash("Assignment title is required.", "danger")
            return render_template("teacher/edit_assignment.html", teacher=teacher, course=course, assignment=assignment, current_attachment=current_attachment, current_attachment_name=current_attachment_name, **_teacher_nav_context(teacher))

        try:
            start_date = _parse_datetime(request.form.get("start_date"), "Start date")
            due_date = _parse_datetime(request.form.get("due_date"), "Due date")
            if due_date <= start_date:
                raise ValueError("Due date must be after the start date.")
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("teacher/edit_assignment.html", teacher=teacher, course=course, assignment=assignment, current_attachment=current_attachment, current_attachment_name=current_attachment_name, **_teacher_nav_context(teacher))

        assignment_file = request.files.get("assignment_file")
        remove_attachment = request.form.get("remove_attachment") == "1"
        saved_new_file = None

        if assignment_file and assignment_file.filename:
            if not allowed_file(assignment_file.filename):
                flash("Unsupported assignment file type.", "danger")
                return render_template("teacher/edit_assignment.html", teacher=teacher, course=course, assignment=assignment, current_attachment=current_attachment, current_attachment_name=current_attachment_name, **_teacher_nav_context(teacher))

            try:
                original_name = secure_filename(assignment_file.filename)
                saved_new_file = f"assignment_{assignment.id}_{uuid.uuid4().hex}_{original_name}"
                upload_target = '/tmp/uploads' if os.environ.get('VERCEL') else UPLOAD_FOLDER
                os.makedirs(upload_target, exist_ok=True)
                assignment_file.save(os.path.join(upload_target, saved_new_file))
            except Exception:
                saved_new_file = None

        try:
            assignment.title = title
            assignment.description = description
            assignment.assignment_type = assignment_type
            assignment.start_date = start_date
            assignment.due_date = due_date
            db.session.commit()

            if saved_new_file or remove_attachment:
                for old_filename in current_attachments:
                    old_path = os.path.join(UPLOAD_FOLDER, old_filename)
                    if os.path.isfile(old_path):
                        os.remove(old_path)

            try:
                notify_course_students(course, "Assignment updated", f"‘{title}’ was updated in {course.name}.", f"/student/courses/{course.id}")
                db.session.commit()
            except Exception:
                db.session.rollback()

        except Exception as exc:
            db.session.rollback()
            if saved_new_file:
                new_path = os.path.join(UPLOAD_FOLDER, saved_new_file)
                if os.path.isfile(new_path):
                    os.remove(new_path)
            flash(f"Unable to update the assignment: {exc}", "danger")
            return render_template("teacher/edit_assignment.html", teacher=teacher, course=course, assignment=assignment, current_attachment=current_attachment, current_attachment_name=current_attachment_name, **_teacher_nav_context(teacher))

        flash("Assignment updated successfully.", "success")
        return redirect(url_for("teachers.view_course", teacher_id=teacher.id, course_id=course.id))

    return render_template("teacher/edit_assignment.html", teacher=teacher, course=course, assignment=assignment, current_attachment=current_attachment, current_attachment_name=current_attachment_name, **_teacher_nav_context(teacher))


# ------------------------- Preview Exam -------------------------
@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/exams/<int:exam_id>/preview")
@login_required
def preview_exam(teacher_id, course_id, exam_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.get_or_404(course_id)
    exam = Exam.query.get_or_404(exam_id)
    return render_template("teacher/preview_exam.html", teacher=teacher, course=course, exam=exam)


# ------------------------- Edit Exam -------------------------
@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/exams/<int:exam_id>/edit", methods=["GET", "POST"])
@login_required
def edit_exam_page(teacher_id, course_id, exam_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.get_or_404(course_id)
    exam = Exam.query.get_or_404(exam_id)

    if request.method == "POST":
        exam.title = request.form.get("title")
        exam.description = request.form.get("description")
        exam.total_score = float(request.form.get("total_score"))
        exam.start_date = datetime.fromisoformat(request.form.get("start_date"))
        exam.end_date = datetime.fromisoformat(request.form.get("end_date"))

        db.session.commit()
        flash("Exam updated successfully.", "success")
        return redirect(url_for("teachers.view_course", teacher_id=teacher.id, course_id=course.id))

    return render_template("teacher/edit_exam.html", teacher=teacher, course=course, exam=exam)


# ------------------------- Update Student Quiz Score -------------------------
@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/quiz/<int:quiz_id>/student/<int:student_id>/update", methods=["POST"])
@login_required
def update_student_quiz_score(teacher_id, course_id, quiz_id, student_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    assignment_id = quiz.assignment_id

    submission = Submission.query.filter_by(student_id=student_id, assignment_id=assignment_id).first()
    new_grade = request.form.get("score", type=float)

    if submission:
        submission.grade = new_grade
    else:
        submission = Submission(student_id=student_id, assignment_id=assignment_id, grade=new_grade)
        db.session.add(submission)

    try:
        db.session.add(Notification(user_id=student_id, title='Quiz grade published', message=f'Your grade for {quiz.title} has been updated.', link=f'/student/courses/{course_id}'))
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({"status": "success", "message
