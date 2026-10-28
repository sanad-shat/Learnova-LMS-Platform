from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from flask_login import login_required, current_user, login_user, logout_user
from app.models import (
    User, Course, Unit, Assignment, Quiz, QuizQuestion, 
    Exam, Grade, Activity, Notification, Certificate,
    ExamQuestion, Enrollment, Submission
)
from PIL import Image, ImageDraw, ImageFont
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy.orm import joinedload
from app import db, login_manager
from app.services import notify_course_students, course_progress, final_grade, issue_certificate
import os
import uuid

# Try to import StudentActivity (used in student tracking)
try:
    from app.models import StudentActivity
except ImportError:
    StudentActivity = None

teachers_bp = Blueprint("teachers", __name__, url_prefix="/teacher")

# Upload configuration safe for Vercel/Serverless
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
    """Return True when an uploaded file has an allowed extension."""
    if not filename:
        return False
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _parse_datetime(value, label):
    """Parse a datetime-local form value and provide a clear validation error."""
    if not value:
        raise ValueError(f"{label} is required.")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {label.lower()}.") from exc


def _question_numbers(form):
    """Return sorted dynamic question indexes from question_1, question_2, ... fields."""
    numbers = []
    for key in form.keys():
        if key.startswith("question_"):
            suffix = key.removeprefix("question_")
            if suffix.isdigit():
                numbers.append(int(suffix))
    return sorted(set(numbers))


def _question_payload(form, number):
    """Validate and normalize a quiz/exam question submitted by the builder UI."""
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
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


def _teacher_nav_context(teacher):
    ungraded = Submission.query.join(Assignment).join(Course).filter(Course.teacher_id == teacher.id, Submission.grade.is_(None)).count()
    unread = Notification.query.filter_by(user_id=teacher.id, is_read=False).count()
    return {'nav_ungraded': ungraded, 'nav_notifications': unread}


# ------------------------- Authentication -------------------------
@teachers_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle teacher login with demo bypass support."""
    if current_user.is_authenticated and getattr(current_user, 'role', '').lower() == "teacher":
        return redirect(url_for("teachers.dashboard", teacher_id=current_user.id))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        # 1. الدخول التجريبي المباشر
        if (email in ["instructor@learnova.edu", "demo_instructor", "teacher@learnova.edu", "demo@learnova.edu"]) and password == "demo123":
            try:
                db.session.rollback()
                demo_teacher = User.query.filter(User.role.ilike("teacher")).first()
                if demo_teacher:
                    session['is_demo'] = True
                    login_user(demo_teacher)
                    flash("Signed in successfully with Demo Instructor Account.", "success")
                    return redirect(url_for("teachers.dashboard", teacher_id=demo_teacher.id))
            except Exception:
                db.session.rollback()

        # 2. التحقق العادي لباقي المستخدمين
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
                return redirect(url_for("teachers.dashboard", teacher_id=user.id))
        except Exception:
            db.session.rollback()

        flash("Invalid credentials or not authorized as an instructor.", "danger")
    return render_template("teacher/login.html")


@teachers_bp.route("/logout")
@login_required
def logout():
    """Log out the current teacher."""
    session.pop('is_demo', None)
    logout_user()
    return redirect(url_for("teachers.login"))


# ------------------------- Dashboard -------------------------
@teachers_bp.route("/<int:teacher_id>/dashboard")
@login_required
def dashboard(teacher_id):
    """Main dashboard showing teacher info and courses."""
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
    """Display all courses taught by the teacher."""
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
    """Display all students enrolled in the teacher's courses."""
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
    """Display all assignments in all courses."""
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
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
                except Exception:
                    filename = None

        try:
            unit = Unit(title=title, file_path=filename, course_id=course_id)
            db.session.add(unit)
            db.session.flush()
            try:
                notify_course_students(course, 'New learning unit', f'A new unit “{title}” was added to {course.name}.', f'/student/courses/{course.id}')
            except Exception:
                pass
            db.session.commit()
            flash("Unit added successfully.", "success")
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
                    assignment_file.save(os.path.join(UPLOAD_FOLDER, stored_name))
                except Exception:
                    pass

            try:
                notify_course_students(
                    course,
                    "New assignment",
                    f"‘{title}’ was added to {course.name}. Due: {due_date:%d %b %Y %H:%M}.",
                    f"/student/courses/{course.id}",
                )
            except Exception:
                pass

            db.session.commit()
            flash("Assignment created successfully.", "success")
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

            try:
                notify_course_students(course, "New quiz", f"‘{title}’ is now available in {course.name}.", f"/student/courses/{course.id}")
            except Exception:
                pass

            db.session.commit()
            flash(f"Quiz created successfully with {len(questions)} questions.", "success")
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

            try:
                notify_course_students(course, "New exam", f"‘{title}’ is now available in {course.name}.", f"/student/courses/{course.id}")
            except Exception:
                pass

            db.session.commit()
            flash(f"Exam created successfully with {len(questions)} questions.", "success")
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
                file.save(os.path.join(UPLOAD_FOLDER, filename))
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
                assignment_file.save(os.path.join(UPLOAD_FOLDER, saved_new_file))
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
            except Exception:
                pass
            db.session.commit()

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
    except Exception:
        pass
    db.session.commit()
    return jsonify({"status": "success", "message": "Grade updated"})


@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/exam/<int:exam_id>/student/<int:student_id>/update", methods=["POST"])
@login_required
def update_student_exam_score(teacher_id, course_id, exam_id, student_id):
    exam = Exam.query.get_or_404(exam_id)
    new_score = request.form.get("score", type=float)

    grade = Grade.query.filter_by(exam_id=exam.id, student_id=student_id).first()
    if grade:
        grade.score = new_score
    else:
        grade = Grade(exam_id=exam.id, student_id=student_id, score=new_score)
        db.session.add(grade)

    try:
        db.session.add(Notification(user_id=student_id, title='Exam grade published', message=f'Your grade for {exam.title} has been updated.', link=f'/student/courses/{course_id}'))
    except Exception:
        pass
    db.session.commit()
    return jsonify({"status": "success", "message": "Exam grade updated"})


def generate_signature_image(teacher_name, signature_id):
    sig_dir = os.path.join(UPLOAD_FOLDER, "signatures") if os.environ.get('VERCEL') else os.path.join("app", "static", "signatures")
    try:
        os.makedirs(sig_dir, exist_ok=True)
    except Exception:
        pass

    filename = f"signature_{signature_id}.png"
    filepath = os.path.join(sig_dir, filename)

    if os.path.exists(filepath):
        return filename

    try:
        width, height = 400, 80
        img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("app/static/fonts/DancingScript-Bold.ttf", 48)
        except Exception:
            font = ImageFont.load_default()

        draw.text((10, 10), teacher_name, fill=(0, 0, 0, 255), font=font)
        img.save(filepath)
    except Exception:
        pass
    return filename


@teachers_bp.route("/<int:teacher_id>/courses/<int:course_id>/student/<int:student_id>/certificate")
@login_required
def generate_certificate(teacher_id, course_id, student_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.get_or_404(course_id)
    student = User.query.get_or_404(student_id)

    quizzes = []
    for quiz in course.quizzes:
        submissions = Submission.query.filter_by(student_id=student.id, assignment_id=quiz.assignment_id).all()
        total_score = sum(sub.grade for sub in submissions) if submissions else 0
        quizzes.append({"completed": bool(submissions), "score": total_score})

    exams = []
    for exam in course.exams:
        grade = Grade.query.filter_by(student_id=student.id, exam_id=exam.id).first()
        exams.append({
            "completed": bool(grade),
            "score": grade.score if grade else 0
        })

    activity = Activity.query.filter_by(student_id=student.id, course_id=course.id).first()
    activity_score = activity.score if activity else None

    can_print = (
        all(q["completed"] and q["score"] >= 0 for q in quizzes) and
        all(e["completed"] and e["score"] >= 0 for e in exams) and
        activity_score is not None
    )

    if not can_print:
        flash("لا يمكن إصدار الشهادة — الطالب لم ينهِ جميع المهام.", "warning")
        return redirect(url_for("teachers.view_course", teacher_id=teacher_id, course_id=course_id))

    total_quizzes_score = sum(q["score"] for q in quizzes)
    total_quizzes_possible = sum(sum(qq.score for qq in quiz.questions) for quiz in course.quizzes)
    total_exams_score = sum(e["score"] for e in exams)
    total_exams_possible = sum(exam.total_score for exam in course.exams)
    total_score = total_quizzes_score + total_exams_score + activity_score
    total_possible = total_quizzes_possible + total_exams_possible + 100

    percentage = round((total_score / total_possible) * 100, 2) if total_possible > 0 else 0
    signature_filename = generate_signature_image(teacher.username, teacher.id)

    return render_template(
        "teacher/certificate.html",
        teacher=teacher,
        course=course,
        student=student,
        total_score=round(total_score, 2),
        total_possible=total_possible,
        percentage=percentage,
        quizzes=quizzes,
        exams=exams,
        activity_score=activity_score,
        today=datetime.now(),
        signature_url=url_for('static', filename=f'signatures/{signature_filename}')
    )


@teachers_bp.route('/<int:teacher_id>/certificates')
@login_required
def certificates(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    if current_user.id != teacher.id or current_user.role.lower() != 'teacher':
        flash('Access denied.', 'danger')
        return redirect(url_for('teachers.login'))
    rows = []
    for course in Course.query.filter_by(teacher_id=teacher.id).all():
        students = []
        for enrollment in course.enrollments:
            student = enrollment.student
            students.append({
                'student': student,
                'progress': course_progress(student, course),
                'grade': final_grade(student, course),
                'certificate': Certificate.query.filter_by(student_id=student.id, course_id=course.id).first()
            })
        rows.append({'course': course, 'students': students})
    count = Certificate.query.join(Course).filter(Course.teacher_id == teacher.id).count()
    return render_template('teacher/certificates.html', teacher=teacher, rows=rows, certificate_count=count, active_page='certificates', **_teacher_nav_context(teacher))


@teachers_bp.route('/<int:teacher_id>/courses/<int:course_id>/student/<int:student_id>/issue-certificate')
@login_required
def issue_student_certificate(teacher_id, course_id, student_id):
    teacher = User.query.get_or_404(teacher_id)
    course = Course.query.get_or_404(course_id)
    student = User.query.get_or_404(student_id)
    if current_user.id != teacher.id or course.teacher_id != teacher.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('teachers.login'))
    certificate, progress, grade = issue_certificate(student, course)
    if certificate:
        flash('Certificate issued successfully.', 'success')
    else:
        flash(f'Student is not eligible yet. Progress: {progress["percent"]}%, grade: {grade}%.', 'warning')
    return redirect(url_for('teachers.certificates', teacher_id=teacher.id))


@teachers_bp.route('/<int:teacher_id>/submissions')
@login_required
def submissions(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    if current_user.id != teacher.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('teachers.login'))
    items = Submission.query.join(Assignment).join(Course).filter(Course.teacher_id == teacher.id).order_by(Submission.submitted_at.desc()).all()
    return render_template('teacher/submissions.html', teacher=teacher, submissions=items, **_teacher_nav_context(teacher))


@teachers_bp.route('/<int:teacher_id>/submission/<int:submission_id>/grade', methods=['POST'])
@login_required
def grade_submission(teacher_id, submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if current_user.id != teacher_id or submission.assignment.course.teacher_id != teacher_id:
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    score = request.form.get('grade', type=float)
    feedback = request.form.get('feedback', '').strip()
    if score is None or score < 0 or score > 100:
        flash('Grade must be between 0 and 100.', 'danger')
    else:
        submission.grade = score
        submission.feedback = feedback
        try:
            db.session.add(Notification(user_id=submission.student_id, title='Assignment graded', message=f'Your submission for {submission.assignment.title} received {score}/100.', link=f'/student/courses/{submission.assignment.course_id}'))
        except Exception:
            pass
        db.session.commit()
        flash('Submission graded successfully.', 'success')
    return redirect(url_for('teachers.submissions', teacher_id=teacher_id))


@teachers_bp.route('/<int:teacher_id>/evaluations')
@login_required
def evaluations(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    if current_user.id != teacher.id or current_user.role != 'teacher':
        flash('Access denied.', 'danger')
        return redirect(url_for('teachers.login'))
    submissions = Submission.query.join(Assignment).join(Course).filter(Course.teacher_id == teacher.id).all()
    exam_grades = Grade.query.join(Exam).join(Course).filter(Course.teacher_id == teacher.id).all()
    graded = [x for x in submissions if x.grade is not None]
    scores = [x.grade for x in graded] + [g.score for g in exam_grades if g.score is not None]
    rows = []
    for x in sorted(graded, key=lambda z: z.submitted_at or datetime.min, reverse=True):
        rows.append({'student': x.student.name_person or x.student.username, 'course': x.assignment.course.code, 'title': x.assignment.title, 'type': 'Assignment', 'score': f'{x.grade:.1f}/100'})
    for g in exam_grades:
        rows.append({'student': g.student.name_person or g.student.username, 'course': g.exam.course.code, 'title': g.exam.title, 'type': 'Exam', 'score': f'{g.score:.1f}/{g.exam.total_score:g}'})
    average = round(sum(scores)/len(scores), 1) if scores else 0
    return render_template('teacher/evaluations.html', teacher=teacher, graded_submissions=len(graded), pending_submissions=len(submissions)-len(graded), exam_grades=exam_grades, average_score=average, evaluation_rows=rows[:100], **_teacher_nav_context(teacher))


@teachers_bp.route('/<int:teacher_id>/reports')
@login_required
def reports(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    if current_user.id != teacher.id or current_user.role != 'teacher':
        flash('Access denied.', 'danger')
        return redirect(url_for('teachers.login'))
    courses = Course.query.filter_by(teacher_id=teacher.id).all()
    student_ids = {e.student_id for c in courses for e in c.enrollments}
    submissions = Submission.query.join(Assignment).join(Course).filter(Course.teacher_id == teacher.id).all()
    report = {'courses': len(courses), 'students': len(student_ids), 'submissions': len(submissions), 'ungraded': sum(1 for s in submissions if s.grade is None)}
    course_reports = []
    for c in courses:
        scores = [s.grade for a in c.assignments for s in a.submissions if s.grade is not None]
        scores += [g.score for e in c.exams for g in e.grades if g.score is not None]
        avg = round(sum(scores)/len(scores), 1) if scores else 0
        course_reports.append({'code': c.code, 'name': c.name, 'students': len(c.enrollments), 'assignments': len(c.assignments), 'quizzes': len(c.quizzes), 'exams': len(c.exams), 'average': avg})
    return render_template('teacher/reports.html', teacher=teacher, report=report, course_reports=course_reports, **_teacher_nav_context(teacher))


@teachers_bp.route('/<int:teacher_id>/profile', methods=['GET', 'POST'])
@login_required
def profile(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    if current_user.id != teacher.id or current_user.role != 'teacher':
        flash('Access denied.', 'danger')
        return redirect(url_for('teachers.login'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        duplicate = User.query.filter(User.email == email, User.id != teacher.id).first()
        if duplicate:
            flash('This email is already used by another account.', 'danger')
        else:
            teacher.name_person = request.form.get('name_person', '').strip()
            teacher.email = email
            teacher.phone = request.form.get('phone', '').strip()
            teacher.department = request.form.get('department', '').strip()
            teacher.academic_rank = request.form.get('academic_rank', '').strip()
            teacher.office_number = request.form.get('office_number', '').strip()
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('teachers.profile', teacher_id=teacher.id))
    return render_template('teacher/profile.html', teacher=teacher, **_teacher_nav_context(teacher))


@teachers_bp.route('/<int:teacher_id>/notifications')
@login_required
def notifications(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    if current_user.id != teacher.id or current_user.role != 'teacher':
        flash('Access denied.', 'danger')
        return redirect(url_for('teachers.login'))
    items = Notification.query.filter_by(user_id=teacher.id).order_by(Notification.created_at.desc()).all()
    return render_template('teacher/notifications.html', teacher=teacher, notifications=items, **_teacher_nav_context(teacher))


@teachers_bp.route('/<int:teacher_id>/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read(teacher_id):
    if current_user.id != teacher_id or current_user.role != 'teacher':
        return jsonify({'status': 'error'}), 403
    Notification.query.filter_by(user_id=teacher_id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('teachers.notifications', teacher_id=teacher_id))


def _owns_course(teacher_id, course):
    return current_user.is_authenticated and current_user.role == 'teacher' and current_user.id == teacher_id and course.teacher_id == teacher_id


@teachers_bp.route('/<int:teacher_id>/courses/<int:course_id>/units/<int:unit_id>/delete', methods=['POST'])
@login_required
def delete_unit(teacher_id, course_id, unit_id):
    course = Course.query.get_or_404(course_id)
    unit = Unit.query.get_or_404(unit_id)
    if not _owns_course(teacher_id, course) or unit.course_id != course.id:
        flash('Access denied.', 'danger')
    else:
        if unit.file_path:
            path = os.path.join(UPLOAD_FOLDER, unit.file_path)
            if os.path.isfile(path):
                os.remove(path)
        db.session.delete(unit)
        db.session.commit()
        flash('Unit deleted successfully.', 'success')
    return redirect(url_for('teachers.view_course', teacher_id=teacher_id, course_id=course_id))


@teachers_bp.route('/<int:teacher_id>/courses/<int:course_id>/assignments/<int:assignment_id>/delete', methods=['POST'])
@login_required
def delete_assignment(teacher_id, course_id, assignment_id):
    course = Course.query.get_or_404(course_id)
    item = Assignment.query.get_or_404(assignment_id)
    if not _owns_course(teacher_id, course) or item.course_id != course.id:
        flash('Access denied.', 'danger')
    else:
        db.session.delete(item)
        db.session.commit()
        flash('Assignment deleted successfully.', 'success')
    return redirect(url_for('teachers.view_course', teacher_id=teacher_id, course_id=course_id))


@teachers_bp.route('/<int:teacher_id>/courses/<int:course_id>/quizzes/<int:quiz_id>/delete', methods=['POST'])
@login_required
def delete_quiz(teacher_id, course_id, quiz_id):
    course = Course.query.get_or_404(course_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    if not _owns_course(teacher_id, course) or quiz.course_id != course.id:
        flash('Access denied.', 'danger')
    else:
        assignment = quiz.assignment
        db.session.delete(assignment if assignment else quiz)
        db.session.commit()
        flash('Quiz deleted successfully.', 'success')
    return redirect(url_for('teachers.view_course', teacher_id=teacher_id, course_id=course_id))


@teachers_bp.route('/<int:teacher_id>/courses/<int:course_id>/exams/<int:exam_id>/delete', methods=['POST'])
@login_required
def delete_exam(teacher_id, course_id, exam_id):
    course = Course.query.get_or_404(course_id)
    exam = Exam.query.get_or_404(exam_id)
    if not _owns_course(teacher_id, course) or exam.course_id != course.id:
        flash('Access denied.', 'danger')
    else:
        db.session.delete(exam)
        db.session.commit()
        flash('Exam deleted successfully.', 'success')
    return redirect(url_for('teachers.view_course', teacher_id=teacher_id, course_id=course_id))


@teachers_bp.route('/<int:teacher_id>/courses/<int:course_id>/students/<int:student_id>/activity/delete', methods=['POST'])
@login_required
def delete_activity(teacher_id, course_id, student_id):
    course = Course.query.get_or_404(course_id)
    if not _owns_course(teacher_id, course):
        flash('Access denied.', 'danger')
    else:
        Activity.query.filter_by(student_id=student_id, course_id=course_id).delete()
        db.session.commit()
        flash('Activity score removed.', 'success')
    return redirect(url_for('teachers.view_course', teacher_id=teacher_id, course_id=course_id))
