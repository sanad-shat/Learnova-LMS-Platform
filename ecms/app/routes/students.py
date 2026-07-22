from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, json
from flask_login import login_user, logout_user, login_required, current_user
from app.models import (
    User,
    Course,
    Quiz,
    Exam,
    Submission,
    Grade,
    Activity,
    Assignment,
    Enrollment,
    QuizQuestion,
    ExamQuestion,
    get_question_answer,
    Unit,
    UnitCompletion,
    Notification,
    Certificate
)
from app import db
from datetime import datetime, timezone
import os
import uuid
from PIL import Image, ImageDraw, ImageFont
from werkzeug.utils import secure_filename
from app.utils import check_answer
from app.services import course_progress, final_grade, issue_certificate

students_bp = Blueprint("students", __name__, url_prefix="/student")


# ------------------------- Student Login -------------------------
@students_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.role.lower() == "student":
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("students.dashboard"))
        else:
            flash("Invalid email or password, or you don't have permission to login as a student.", "danger")
    return render_template("student/login.html")


# ------------------------- Student Logout -------------------------
@students_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("students.login"))


# ------------------------- Student Dashboard -------------------------
@students_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role.lower() != "student":
        flash("Access denied. Students only.", "danger")
        return redirect(url_for("students.login"))

    course_cards = []
    for enrollment in current_user.enrollments:
        course = enrollment.course
        progress = course_progress(current_user, course)
        grade = final_grade(current_user, course)
        cert = Certificate.query.filter_by(student_id=current_user.id, course_id=course.id).first()
        course_cards.append({'course': course, 'progress': progress, 'grade': grade, 'certificate': cert})

    overall = round(sum(c['progress']['percent'] for c in course_cards) / len(course_cards)) if course_cards else 0
    pending = sum(max(0, c['progress']['total'] - c['progress']['completed']) for c in course_cards)
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(8).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    certificates = Certificate.query.filter_by(student_id=current_user.id).order_by(Certificate.issued_at.desc()).all()
    return render_template('student/dashboard.html', student=current_user, course_cards=course_cards,
                           overall_progress=overall, pending_items=pending, notifications=notifications,
                           unread_count=unread_count, certificates=certificates, active_page='dashboard',
                           **_student_nav_context(current_user))

# ------------------------- View Course Details -------------------------
@students_bp.route("/courses/<int:course_id>")
@login_required
def view_course(course_id):
    if current_user.role.lower() != "student":
        flash("Access denied.", "danger")
        return redirect(url_for("students.login"))
    enrollment = Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first()
    if not enrollment:
        flash("You are not enrolled in this course.", "warning")
        return redirect(url_for("students.dashboard"))

    course = Course.query.options(
        db.joinedload(Course.units), db.joinedload(Course.assignments),
        db.joinedload(Course.quizzes).joinedload(Quiz.questions), db.joinedload(Course.exams)
    ).get_or_404(course_id)
    completed_unit_ids = {x.unit_id for x in UnitCompletion.query.filter_by(student_id=current_user.id).all()}
    assignments = []
    for assignment in course.assignments:
        if assignment.assignment_type == 'quiz':
            continue
        submission = Submission.query.filter_by(student_id=current_user.id, assignment_id=assignment.id).first()
        assignments.append({'assignment': assignment, 'submitted': bool(submission),
                            'grade': submission.grade if submission else None,
                            'is_late': bool(submission and assignment.due_date and submission.submitted_at and submission.submitted_at > assignment.due_date),
                            'submission_id': submission.id if submission else None})
    quizzes = []
    for quiz in course.quizzes:
        submission = Submission.query.filter_by(student_id=current_user.id, assignment_id=quiz.assignment_id).first()
        quizzes.append({'quiz': quiz, 'attempted': bool(submission), 'score': submission.grade if submission else None,
                        'total': sum(q.score for q in quiz.questions) or 1})
    exams = []
    for exam in course.exams:
        grade = Grade.query.filter_by(student_id=current_user.id, exam_id=exam.id).first()
        exams.append({'exam': exam, 'taken': bool(grade), 'score': grade.score if grade else None})
    progress = course_progress(current_user, course)
    grade = final_grade(current_user, course)
    certificate = Certificate.query.filter_by(student_id=current_user.id, course_id=course.id).first()
    return render_template('student/view_course.html', student=current_user, course=course, teacher=course.teacher,
                           assignments=assignments, quizzes=quizzes, exams=exams, progress=progress,
                           final_grade=grade, certificate=certificate, completed_unit_ids=completed_unit_ids)

# ------------------------- Take Quiz -------------------------
@students_bp.route("/quiz/<int:quiz_id>/take", methods=["GET", "POST"])
@login_required
def take_quiz(quiz_id):
    quiz = Quiz.query.options(db.joinedload(Quiz.questions)).get_or_404(quiz_id)
    enrollment = next((e for e in current_user.enrollments if e.course_id == quiz.course.id), None)
    if not enrollment:
        flash("You are not enrolled in this course.", "warning")
        return redirect(url_for("students.dashboard"))

    if not quiz.questions:
        flash("This quiz has no questions yet.", "warning")
        return redirect(url_for("students.view_course", course_id=quiz.course.id))

    existing = Submission.query.filter_by(student_id=current_user.id, assignment_id=quiz.assignment_id).first()
    now = datetime.now(timezone.utc)
    end = quiz.end_date
    if end and end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if end and now > end:
        flash('This quiz is closed.', 'warning')
        return redirect(url_for('students.view_course', course_id=quiz.course.id))
    if existing:
        flash('You have already submitted this quiz.', 'info')
        return redirect(url_for('students.quiz_results', quiz_id=quiz.id))

    if request.method == "POST":
        total_score = 0
        student_answers = {}

        for question in quiz.questions:
            answer_key = f"answer_{question.id}"
            student_answer = (request.form.get(answer_key, "") or "").strip()
            student_answers[str(question.id)] = student_answer

            correct_answer = (question.answer or "").strip()
            is_correct = False

            is_correct = check_answer(student_answer, correct_answer, question.question_type)

            if is_correct:
                total_score += question.score
            elif not correct_answer:
                print(f"⚠️ Warning: Question ID {question.id} has no correct answer set!")

        submission = Submission(
            student_id=current_user.id,
            assignment_id=quiz.assignment_id,
            grade=total_score,
            submission_text=json.dumps(student_answers, ensure_ascii=False),
            submitted_at=datetime.now(timezone.utc)
        )
        db.session.add(submission)
        db.session.commit()

        flash(f"Quiz submitted! Your score: {total_score} / {sum(q.score for q in quiz.questions)}", "success")
        return redirect(url_for("students.quiz_results", quiz_id=quiz.id))

    return render_template("student/take_quiz.html", quiz=quiz, student=current_user, active_page="courses", **_student_nav_context(current_user))


# ------------------------- Quiz Results (محدثة بالكامل) -------------------------
@students_bp.route('/quiz/results/<int:quiz_id>')
@login_required
def quiz_results(quiz_id):
    """
    عرض نتائج الكويز للطالب بعد التسليم.
    يعتمد على جلب الإجابات من قاعدة البيانات (Submission) وليس من الجلسة.
    يستخدم دالة get_question_answer لجلب الإجابات الصحيحة من قاعدة البيانات.
    """
    # 1. جلب الكويز
    quiz = Quiz.query.get_or_404(quiz_id)

    # 2. التحقق من تسجيل الطالب في الكورس
    enrollment = next((e for e in current_user.enrollments if e.course_id == quiz.course_id), None)
    if not enrollment:
        flash("You are not enrolled in this course.", "warning")
        return redirect(url_for("students.dashboard"))

    # 3. جلب آخر تسليم لهذا الكويز من هذا الطالب
    submission = Submission.query.filter_by(
        student_id=current_user.id,
        assignment_id=quiz.assignment_id
    ).order_by(Submission.submitted_at.desc()).first()

    if not submission:
        flash("No submission found for this quiz.", "danger")
        return redirect(url_for("students.view_course", course_id=quiz.course_id))

    # 4. فك ترميز إجابات الطالب من JSON
    try:
        student_answers = json.loads(submission.submission_text)  # {"1": "باريس", "2": "True", ...}
    except:
        student_answers = {}

    # 5. جلب الأسئلة
    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()

    # 6. تحضير النتائج
    results = []
    obtained_score = 0
    total_score = sum(q.score for q in questions)

    for q in questions:
        correct_answer = get_question_answer(q.id, 'quiz') or ""
        student_answer = student_answers.get(str(q.id), "")  # تخزين الأسئلة كـ string keys

        # تطبيع للعرض والمقارنة
        student_norm = str(student_answer).strip().lower().replace(' ', '')
        correct_norm = str(correct_answer).strip().lower().replace(' ', '')

        # تحديد الصحة حسب نوع السؤال
        if q.question_type == 'multiple':
            try:
                s_list = sorted([x.strip() for x in student_norm.split(',') if x.strip()])
                c_list = sorted([x.strip() for x in correct_norm.split(',') if x.strip()])
                is_correct = s_list == c_list
            except:
                is_correct = False
        else:
            is_correct = student_norm == correct_norm

        if is_correct:
            obtained_score += q.score

        results.append({
            'id': q.id,
            'question_text': q.question_text,
            'student_answer': student_answer,
            'correct_answer': correct_answer,
            'score': q.score,
            'question_type': q.question_type,
            'is_correct': is_correct
        })

    # 7. عرض القالب
    return render_template(
        'student/quiz_results.html',  # ⚠️ تأكد من وجود الملف هنا
        quiz=quiz,
        results=results,
        obtained_score=submission.grade if submission.grade is not None else obtained_score,
        total_score=total_score,
        student=current_user, active_page='grades', **_student_nav_context(current_user)
    )



# ------------------------- Take Exam -------------------------
@students_bp.route("/exam/<int:exam_id>/take", methods=["GET", "POST"])
@login_required
def take_exam(exam_id):
    exam = Exam.query.options(
        db.joinedload(Exam.questions)
    ).get_or_404(exam_id)

    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=exam.course_id
    ).first()

    if not enrollment:
        flash("You are not enrolled in this course.", "warning")
        return redirect(url_for("students.dashboard"))

    if not exam.questions:
        flash("This exam has no questions yet.", "warning")
        return redirect(
            url_for("students.view_course", course_id=exam.course_id)
        )

    existing_grade = Grade.query.filter_by(
        student_id=current_user.id,
        exam_id=exam.id
    ).first()

    if existing_grade:
        flash("You have already submitted this exam.", "info")
        return redirect(
            url_for("students.exam_results", exam_id=exam.id)
        )

    now = datetime.now(timezone.utc)

    start_date = exam.start_date
    end_date = exam.end_date

    if start_date and start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)

    if end_date and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    if start_date and now < start_date:
        flash("This exam is not available yet.", "warning")
        return redirect(
            url_for("students.view_course", course_id=exam.course_id)
        )

    if end_date and now > end_date:
        flash("This exam is closed.", "warning")
        return redirect(
            url_for("students.view_course", course_id=exam.course_id)
        )

    if request.method == "POST":
        total_score = 0

        for question in exam.questions:
            answer_key = f"answer_{question.id}"
            student_answer = (
                request.form.get(answer_key, "") or ""
            ).strip()

            correct_answer = (question.answer or "").strip()

            if question.question_type == "essay":
                continue

            is_correct = check_answer(
                student_answer,
                correct_answer,
                question.question_type
            )

            if is_correct:
                total_score += float(question.score or 0)

        grade = Grade(
            student_id=current_user.id,
            exam_id=exam.id,
            score=total_score
        )

        db.session.add(grade)
        db.session.commit()

        flash(
            f"Exam submitted successfully. "
            f"Your score is {total_score} / {exam.total_score}.",
            "success"
        )

        return redirect(
            url_for("students.exam_results", exam_id=exam.id)
        )

    return render_template(
        "student/take_exam.html",
        exam=exam,
        student=current_user,
        active_page="courses",
        **_student_nav_context(current_user)
    )


# ------------------------- Exam Results -------------------------
@students_bp.route("/exam/<int:exam_id>/results")
@login_required
def exam_results(exam_id):
    exam = Exam.query.options(
        db.joinedload(Exam.questions)
    ).get_or_404(exam_id)

    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=exam.course_id
    ).first()

    if not enrollment:
        flash("You are not enrolled in this course.", "warning")
        return redirect(url_for("students.dashboard"))

    grade = Grade.query.filter_by(
        student_id=current_user.id,
        exam_id=exam.id
    ).first()

    if not grade:
        flash("You have not submitted this exam yet.", "warning")
        return redirect(
            url_for("students.take_exam", exam_id=exam.id)
        )

    return render_template(
        "student/exam_results.html",
        exam=exam,
        grade=grade,
        student=current_user,
        active_page="grades",
        **_student_nav_context(current_user)
    )
# ------------------------- Edit Submission -------------------------
@students_bp.route('/submission/edit/<int:submission_id>', methods=['GET', 'POST'])
@login_required
def edit_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)

    # تأكد أن الطالب صاحب التسليم
    if submission.student_id != current_user.id:
        flash('لا يمكنك تعديل هذا التسليم.', 'danger')
        return redirect(url_for('students.dashboard'))

    assignment = submission.assignment
    course = assignment.course

    # تحقق من أن التسليم لازال ممكن (قبل تاريخ الاستحقاق مثلاً)
    if assignment.due_date and datetime.now(timezone.utc) > assignment.due_date:
        flash('انتهى وقت تسليم هذا الواجب، لا يمكن التعديل.', 'warning')
        return redirect(url_for('students.view_course', course_id=course.id))

    if request.method == 'POST':
        # تحديث التسليم — مثلاً نص أو ملف
        submission_text = request.form.get('submission_text', '').strip()
        if submission_text:
            submission.submission_text = submission_text
            submission.submitted_at = datetime.now(timezone.utc)
            submission.grade = None  # إعادة التصحيح لاحقًا
            db.session.commit()
            flash('تم تحديث التسليم بنجاح.', 'success')
            return redirect(url_for('students.view_course', course_id=course.id))
        else:
            flash('يرجى إدخال نص التسليم.', 'danger')

    return render_template('student/edit_submission.html', submission=submission, assignment=assignment, student=current_user, active_page='assignments', **_student_nav_context(current_user))


@students_bp.route('/assignment/submit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    course = assignment.course

    # تحقق من تسجيل الطالب في الكورس
    enrollment = next((e for e in current_user.enrollments if e.course_id == course.id), None)
    if not enrollment:
        flash("You are not enrolled in this course.", "warning")
        return redirect(url_for("students.dashboard"))

    # جلب التسليم الحالي إن وجد
    submission = Submission.query.filter_by(
        student_id=current_user.id,
        assignment_id=assignment_id
    ).first()

    now = datetime.now(timezone.utc)
    due = assignment.due_date
    if due and due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    if due and now > due:
        flash('The submission deadline has passed.', 'warning')
        return redirect(url_for('students.view_course', course_id=course.id))

    if request.method == 'POST':
        submission_text = request.form.get('submission_text', '').strip()
        submission_file = request.files.get('submission_file')

        # إذا كان فيه تسليم سابق — نعدله
        if not submission:
            submission = Submission(
                student_id=current_user.id,
                assignment_id=assignment_id
            )

        submission.submission_text = submission_text
        submission.submitted_at = datetime.now(timezone.utc)

        # معالجة رفع الملف (اختياري)
        if submission_file and submission_file.filename:
            original = secure_filename(submission_file.filename)
            filename = f'{uuid.uuid4().hex}_{original}'
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'submissions')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            submission_file.save(filepath)
            submission.submission_file = f"uploads/submissions/{filename}"

        db.session.add(submission)
        db.session.commit()

        flash('تم تسليم الواجب بنجاح!', 'success')
        return redirect(url_for('students.view_course', course_id=course.id))

    return render_template('student/submit_assignment.html', assignment=assignment, submission=submission, student=current_user, active_page='assignments', **_student_nav_context(current_user))

@students_bp.route('/generate_certificate/<int:course_id>')
@login_required
def generate_certificate(course_id):
    if current_user.role.lower() != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('students.login'))

    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id,
    ).first()

    if not enrollment:
        flash('You are not enrolled in this course.', 'warning')
        return redirect(url_for('students.dashboard'))

    certificate, progress, grade = issue_certificate(current_user, course)

    if certificate is None:
        flash(
            f'You need a final grade of at least 60% to receive the certificate. '
            f'Current grade: {grade:.2f}%.',
            'warning',
        )
        return redirect(url_for('students.view_course', course_id=course.id))

    return redirect(url_for('students.certificate', course_id=course.id))


@students_bp.route('/unit/<int:unit_id>/toggle', methods=['POST'])
@login_required
def toggle_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    if not Enrollment.query.filter_by(student_id=current_user.id, course_id=unit.course_id).first():
        flash('You are not enrolled in this course.', 'danger')
        return redirect(url_for('students.dashboard'))
    item = UnitCompletion.query.filter_by(student_id=current_user.id, unit_id=unit.id).first()
    if item:
        db.session.delete(item)
        flash('Unit marked as incomplete.', 'info')
    else:
        db.session.add(UnitCompletion(student_id=current_user.id, unit_id=unit.id))
        flash('Unit completed. Great work!', 'success')
    db.session.commit()
    return redirect(url_for('students.view_course', course_id=unit.course_id))


@students_bp.route('/notifications')
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('student/notifications.html', notifications=items, student=current_user, active_page='notifications', **_student_nav_context(current_user))


@students_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def read_all_notifications():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True}, synchronize_session=False)
    db.session.commit()
    return redirect(url_for('students.notifications'))


@students_bp.route('/certificates')
@login_required
def certificates():
    if current_user.role.lower() != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('students.login'))

    # Automatically create certificates for every enrolled course
    # where the student's final grade is at least 60%.
    for enrollment in current_user.enrollments:
        issue_certificate(current_user, enrollment.course)

    items = Certificate.query.filter_by(
        student_id=current_user.id
    ).order_by(Certificate.issued_at.desc()).all()

    return render_template(
        'student/certificates.html',
        student=current_user,
        certificates=items,
        active_page='certificates',
        **_student_nav_context(current_user),
    )


@students_bp.route('/certificate/<int:course_id>')
@login_required
def certificate(course_id):
    if current_user.role.lower() != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('students.login'))

    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id,
    ).first()

    if not enrollment:
        flash('You are not enrolled in this course.', 'warning')
        return redirect(url_for('students.dashboard'))

    certificate_row, progress, grade = issue_certificate(current_user, course)

    if certificate_row is None:
        flash(
            f'Certificate unavailable. A final grade of at least 60% is required. '
            f'Current grade: {grade:.2f}%.',
            'warning',
        )
        return redirect(url_for('students.view_course', course_id=course.id))

    return render_template(
        'student/certificate.html',
        student=current_user,
        course=course,
        teacher=course.teacher,
        percentage=certificate_row.final_grade,
        certificate=certificate_row,
        today=certificate_row.issued_at,
        progress=progress,
    )



def _student_nav_context(student):
    unread = Notification.query.filter_by(user_id=student.id, is_read=False).count()
    pending_assignments = 0
    upcoming = []
    now = datetime.now(timezone.utc)
    for enrollment in student.enrollments:
        for assignment in enrollment.course.assignments:
            if assignment.assignment_type == 'quiz':
                continue
            submitted = Submission.query.filter_by(student_id=student.id, assignment_id=assignment.id).first()
            if not submitted:
                pending_assignments += 1
                upcoming.append(assignment)
    upcoming.sort(key=lambda x: x.due_date or now)
    return {
        'student_nav_unread': unread,
        'student_nav_pending': pending_assignments,
        'student_upcoming': upcoming[:5],
    }


@students_bp.route('/courses')
@login_required
def courses():
    if current_user.role.lower() != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('students.login'))
    cards = []
    for enrollment in current_user.enrollments:
        course = enrollment.course
        cards.append({
            'course': course,
            'progress': course_progress(current_user, course),
            'grade': final_grade(current_user, course),
            'certificate': Certificate.query.filter_by(student_id=current_user.id, course_id=course.id).first(),
        })
    return render_template('student/courses.html', student=current_user, course_cards=cards,
                           active_page='courses', **_student_nav_context(current_user))


@students_bp.route('/assignments')
@login_required
def assignments():
    if current_user.role.lower() != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('students.login'))
    rows = []
    now = datetime.now(timezone.utc)
    for enrollment in current_user.enrollments:
        for assignment in enrollment.course.assignments:
            if assignment.assignment_type == 'quiz':
                continue
            submission = Submission.query.filter_by(student_id=current_user.id, assignment_id=assignment.id).first()
            due = assignment.due_date
            if due and due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            rows.append({
                'assignment': assignment,
                'submission': submission,
                'is_overdue': bool(due and now > due and not submission),
                'is_late': bool(submission and due and submission.submitted_at and submission.submitted_at.replace(tzinfo=submission.submitted_at.tzinfo or timezone.utc) > due),
            })
    rows.sort(key=lambda x: x['assignment'].due_date or now)
    return render_template('student/assignments.html', student=current_user, assignment_rows=rows,
                           active_page='assignments', **_student_nav_context(current_user))


@students_bp.route('/grades')
@login_required
def grades():
    if current_user.role.lower() != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('students.login'))
    course_rows = []
    for enrollment in current_user.enrollments:
        course = enrollment.course
        assignment_scores = []
        for assignment in course.assignments:
            if assignment.assignment_type == 'quiz':
                continue
            submission = Submission.query.filter_by(student_id=current_user.id, assignment_id=assignment.id).first()
            assignment_scores.append({'title': assignment.title, 'score': submission.grade if submission else None,
                                      'feedback': submission.feedback if submission else None})
        quiz_scores = []
        for quiz in course.quizzes:
            submission = Submission.query.filter_by(student_id=current_user.id, assignment_id=quiz.assignment_id).first()
            total = sum(q.score for q in quiz.questions) or 1
            quiz_scores.append({'title': quiz.title, 'score': submission.grade if submission else None, 'total': total})
        exam_scores = []
        for exam in course.exams:
            grade_row = Grade.query.filter_by(student_id=current_user.id, exam_id=exam.id).first()
            exam_scores.append({'title': exam.title, 'score': grade_row.score if grade_row else None, 'total': exam.total_score})
        course_rows.append({'course': course, 'assignments': assignment_scores, 'quizzes': quiz_scores,
                            'exams': exam_scores, 'final': final_grade(current_user, course)})
    return render_template('student/grades.html', student=current_user, course_rows=course_rows,
                           active_page='grades', **_student_nav_context(current_user))


@students_bp.route('/reports')
@login_required
def reports():
    if current_user.role.lower() != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('students.login'))
    report_rows = []
    for enrollment in current_user.enrollments:
        course = enrollment.course
        progress = course_progress(current_user, course)
        report_rows.append({'course': course, 'progress': progress,
                            'final': final_grade(current_user, course),
                            'certificate': Certificate.query.filter_by(student_id=current_user.id, course_id=course.id).first()})
    return render_template('student/reports.html', student=current_user, report_rows=report_rows,
                           active_page='reports', **_student_nav_context(current_user))


@students_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role.lower() != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('students.login'))
    if request.method == 'POST':
        current_user.name_person = request.form.get('name_person', '').strip() or current_user.name_person
        current_user.phone = request.form.get('phone', '').strip()
        current_user.gender = request.form.get('gender', '').strip()
        new_password = request.form.get('new_password', '').strip()
        if new_password:
            if len(new_password) < 6:
                flash('Password must contain at least 6 characters.', 'warning')
                return redirect(url_for('students.student_profile'))
            current_user.set_password(new_password)
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('students.student_profile'))
    return render_template('student/profile.html', student=current_user, active_page='profile',
                           **_student_nav_context(current_user))


@students_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role.lower() != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('students.login'))
    if request.method == 'POST':
        flash('Your display preferences have been saved for this browser.', 'success')
        return redirect(url_for('students.settings'))
    return render_template('student/settings.html', student=current_user, active_page='settings',
                           **_student_nav_context(current_user))