from uuid import uuid4
from datetime import datetime, timezone

from app import db
from app.models import (
    Submission,
    Grade,
    UnitCompletion,
    Certificate,
    Notification,
)


def course_progress(student, course):
    """Calculate a student's completion percentage for one course."""
    unit_total = len(course.units)
    assignment_items = [
        assignment
        for assignment in course.assignments
        if assignment.assignment_type != "quiz"
    ]
    assignment_total = len(assignment_items)
    quiz_total = len(course.quizzes)
    exam_total = len(course.exams)
    total = unit_total + assignment_total + quiz_total + exam_total

    unit_ids = [unit.id for unit in course.units]
    unit_done = UnitCompletion.query.filter(
        UnitCompletion.student_id == student.id,
        UnitCompletion.unit_id.in_(unit_ids or [-1]),
    ).count()

    assignment_done = sum(
        bool(
            Submission.query.filter_by(
                student_id=student.id,
                assignment_id=assignment.id,
            ).first()
        )
        for assignment in assignment_items
    )

    quiz_done = sum(
        bool(
            Submission.query.filter_by(
                student_id=student.id,
                assignment_id=quiz.assignment_id,
            ).first()
        )
        for quiz in course.quizzes
    )

    exam_done = sum(
        bool(
            Grade.query.filter_by(
                student_id=student.id,
                exam_id=exam.id,
            ).first()
        )
        for exam in course.exams
    )

    completed = unit_done + assignment_done + quiz_done + exam_done
    percent = round(completed * 100 / total) if total else 0

    return {
        "total": total,
        "completed": completed,
        "percent": percent,
        "unit_total": unit_total,
        "unit_done": unit_done,
        "assignment_total": assignment_total,
        "assignment_done": assignment_done,
        "quiz_total": quiz_total,
        "quiz_done": quiz_done,
        "exam_total": exam_total,
        "exam_done": exam_done,
    }


def final_grade(student, course):
    """Calculate a weighted final grade from available assessments."""
    assignment_scores = []
    for assignment in course.assignments:
        if assignment.assignment_type == "quiz":
            continue

        submission = Submission.query.filter_by(
            student_id=student.id,
            assignment_id=assignment.id,
        ).first()

        if submission and submission.grade is not None:
            assignment_scores.append(
                max(0, min(100, float(submission.grade)))
            )

    quiz_scores = []
    for quiz in course.quizzes:
        submission = Submission.query.filter_by(
            student_id=student.id,
            assignment_id=quiz.assignment_id,
        ).first()
        total_score = sum(question.score for question in quiz.questions) or 1

        if submission and submission.grade is not None:
            quiz_scores.append(
                max(
                    0,
                    min(100, float(submission.grade) * 100 / total_score),
                )
            )

    exam_scores = []
    for exam in course.exams:
        grade = Grade.query.filter_by(
            student_id=student.id,
            exam_id=exam.id,
        ).first()

        if grade and grade.score is not None:
            exam_scores.append(
                max(
                    0,
                    min(100, float(grade.score) * 100 / (exam.total_score or 1)),
                )
            )

    components = []
    if assignment_scores:
        components.append((sum(assignment_scores) / len(assignment_scores), 30))
    if quiz_scores:
        components.append((sum(quiz_scores) / len(quiz_scores), 30))
    if exam_scores:
        components.append((sum(exam_scores) / len(exam_scores), 40))

    if not components:
        return 0.0

    total_weight = sum(weight for _, weight in components)
    weighted_score = sum(score * weight for score, weight in components)
    return round(weighted_score / total_weight, 2)


def notify(user_id, title, message, link=None):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
    )
    db.session.add(notification)


def notify_course_students(course, title, message, link=None):
    for enrollment in course.enrollments:
        notify(enrollment.student_id, title, message, link)


def issue_certificate(student, course):
    """
    Create or update a certificate when the student's final grade is at least 60%.

    The function always returns a three-item tuple:
    (certificate_or_none, progress_dictionary, final_grade_number)
    """
    progress = course_progress(student, course)
    grade = float(final_grade(student, course) or 0)

    certificate = Certificate.query.filter_by(
        student_id=student.id,
        course_id=course.id,
    ).first()

    if grade < 60:
        return None, progress, grade

    if certificate is None:
        certificate = Certificate(
            certificate_code=(
                f"LRN-{datetime.now(timezone.utc):%Y%m}-"
                f"{uuid4().hex[:10].upper()}"
            ),
            student_id=student.id,
            course_id=course.id,
            final_grade=grade,
        )
        db.session.add(certificate)

        notify(
            student.id,
            "Certificate Available",
            f"Congratulations! Your certificate for {course.name} is ready.",
            f"/student/certificate/{course.id}",
        )
        db.session.commit()

    elif float(certificate.final_grade or 0) != grade:
        certificate.final_grade = grade
        db.session.commit()

    return certificate, progress, grade
