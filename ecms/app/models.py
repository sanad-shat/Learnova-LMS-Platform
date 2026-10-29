# C:\projectPy27\ecms\app\models.py

from app import db
from flask_login import UserMixin
from datetime import datetime, timezone
import random
from werkzeug.security import generate_password_hash, check_password_hash


# ---------------- User Table ----------------
class User(UserMixin, db.Model):
    """
    Represents a user in the system with roles: student, teacher, or admin.
    Supports plain-text passwords for development/testing.
    """
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True, index=True)
    email = db.Column(db.String(100), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)  # Secure hash
    visible_password = db.Column(db.String(255), nullable=True)  # Demo-only admin display
    role = db.Column(db.String(10), nullable=False)  # 'student', 'teacher', 'admin'
    name_person = db.Column(db.String(100), nullable=True)
    university_id = db.Column(db.String(30), nullable=True, unique=True, index=True)
    employee_id = db.Column(db.String(30), nullable=True, unique=True, index=True)
    phone = db.Column(db.String(25), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    level = db.Column(db.String(30), nullable=True)
    gender = db.Column(db.String(15), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Active')
    office_number = db.Column(db.String(30), nullable=True)
    academic_rank = db.Column(db.String(60), nullable=True)

    # Relationships
    courses = db.relationship('Course', back_populates='teacher', lazy=True)
    enrollments = db.relationship('Enrollment', back_populates='student', lazy=True, cascade='all, delete-orphan')
    submissions = db.relationship('Submission', back_populates='student', lazy=True, cascade='all, delete-orphan')
    grades = db.relationship('Grade', back_populates='student', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and save a password securely."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check modern hashes while keeping legacy plain-text accounts working."""
        if not self.password_hash:
            return False
        try:
            if check_password_hash(self.password_hash, password):
                return True
        except (ValueError, TypeError):
            pass
        return self.password_hash == password

    @property
    def password_status(self):
        value = self.password_hash or ''
        return 'Encrypted' if value.startswith(('scrypt:', 'pbkdf2:')) else value

    @property
    def students(self):
        """
        Get all students enrolled in the courses taught by this teacher.
        Returns a list of unique students.
        """
        all_students = set()
        for course in self.courses:
            for enrollment in course.enrollments:
                all_students.add(enrollment.student)
        return list(all_students)

    def __repr__(self):
        return f"<User {self.username} (role={self.role})>"


# ---------------- Course ID Generator ----------------
def generate_course_id():
    """Generate a random 8-character course identifier (e.g., POIB1234)."""
    letters = 'POIB'
    return ''.join(random.choices(letters, k=4)) + str(random.randint(1000, 9999))


# ---------------- Course Table ----------------
class Course(db.Model):
    """Represents an educational course taught by a teacher."""
    __tablename__ = 'course'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_identifier = db.Column(
        db.String(8), unique=True, nullable=False, default=generate_course_id, index=True
    )

    # Relationships
    teacher = db.relationship('User', back_populates='courses')
    enrollments = db.relationship('Enrollment', back_populates='course', lazy=True, cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', back_populates='course', lazy=True, cascade='all, delete-orphan')
    units = db.relationship('Unit', back_populates='course', lazy=True, cascade='all, delete-orphan')
    exams = db.relationship('Exam', back_populates='course', lazy=True, cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', back_populates='course', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('code', name='uq_course_code'),
    )


# ---------------- Enrollment Table (Student-Course Link) ----------------
class Enrollment(db.Model):
    """Represents a student's enrollment in a course."""
    __tablename__ = 'enrollment'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

    student = db.relationship('User', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')


# ---------------- Assignment Table ----------------
# ---------------- Assignment Table ----------------
class Assignment(db.Model):
    """Represents a homework, quiz, or project assigned in a course."""
    __tablename__ = 'assignment'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    assignment_type = db.Column(db.String(50), nullable=False, default='homework')

    # إضافة start_date و due_date لدعم الفورم
    start_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    due_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

    # Relationships
    course = db.relationship('Course', back_populates='assignments')
    submissions = db.relationship(
        'Submission', back_populates='assignment', lazy=True, cascade='all, delete-orphan'
    )

    # One-to-one with Quiz
    quiz = db.relationship(
        'Quiz',
        back_populates='assignment',
        uselist=False,
        cascade='all, delete-orphan'
    )

def is_quiz(self):
        return self.assignment_type == 'quiz'

# ---------------- Submission Table ----------------
# ---------------- Submission Table ----------------
class Submission(db.Model):
    """Represents a student's submission for an assignment."""
    __tablename__ = 'submission'

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submission_text = db.Column(db.Text)
    submission_file = db.Column(db.String(200))
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))  # <-- ✅ أضف هذا السطر

    # Relationships
    assignment = db.relationship('Assignment', back_populates='submissions')
    student = db.relationship('User', back_populates='submissions')


# ---------------- Unit Table ----------------
class Unit(db.Model):
    """Represents a learning unit within a course (e.g., a lesson or module)."""
    __tablename__ = 'unit'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text)
    file_path = db.Column(db.String(255))

    # Relationship
    course = db.relationship('Course', back_populates='units')


# ---------------- Exam Table ----------------
class Exam(db.Model):
    """Represents an exam in a course with multiple questions."""
    __tablename__ = 'exam'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    total_score = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    course = db.relationship('Course', back_populates='exams', lazy=True)
    grades = db.relationship('Grade', back_populates='exam', lazy=True, cascade='all, delete-orphan')
    questions = db.relationship('ExamQuestion', back_populates='exam', lazy=True, cascade='all, delete-orphan')


# ---------------- Exam Question Table ----------------
class ExamQuestion(db.Model):
    """Represents a single question in an exam."""
    __tablename__ = 'exam_question'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # e.g., 'mcq', 'true_false'
    options = db.Column(db.Text)  # Stores JSON or formatted options
    answer = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float, nullable=False)

    # Relationship
    exam = db.relationship('Exam', back_populates='questions')


# ---------------- Grade Table ----------------
class Grade(db.Model):
    """Represents a student's score in an exam."""
    __tablename__ = 'grade'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Float)

    # Relationships
    exam = db.relationship('Exam', back_populates='grades')
    student = db.relationship('User', back_populates='grades')


# ---------------- Quiz Table ----------------
# ---------------- Quiz Table ----------------
class Quiz(db.Model):
    """Represents a quiz linked to an assignment."""
    __tablename__ = 'quiz'

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    end_date = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    assignment = db.relationship('Assignment', back_populates='quiz')
    course = db.relationship('Course', back_populates='quizzes')
    questions = db.relationship(
        'QuizQuestion',
        back_populates='quiz',
        lazy=True,
        cascade='all, delete-orphan'
    )


# ---------------- Quiz Question Table ----------------

class QuizQuestion(db.Model):
    """Represents a single question in a quiz."""
    __tablename__ = 'quiz_question'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    # حذف assignment_id لأنه زائد
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)
    options = db.Column(db.Text)  # JSON or stringified list
    answer = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=False, default=1)

    # Relationships
    quiz = db.relationship('Quiz', back_populates='questions')
# ---------------- Activity Table ----------------
class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    score = db.Column(db.Float, default=0)

def get_question_answer(question_id, question_type):
    """
Fetch the correct answer for a question by its ID and type.

Parameters:
question_id (int): The ID of the question.
question_type (str): Either 'exam' or 'quiz'.
Returns:
str or None: The correct answer if found, else None.
    """
    if question_type == 'exam':
        question = ExamQuestion.query.get(question_id)
    elif question_type == 'quiz':
        question = QuizQuestion.query.get(question_id)
    else:
        return None  # Invalid question type

    return question.answer if question else None
# ---------------- Platform Enhancements ----------------
class UnitCompletion(db.Model):
    __tablename__ = 'unit_completion'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False, index=True)
    completed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    __table_args__ = (db.UniqueConstraint('student_id', 'unit_id', name='uq_unit_completion'),)
    student = db.relationship('User', backref=db.backref('unit_completions', lazy=True, cascade='all, delete-orphan'))
    unit = db.relationship('Unit', backref=db.backref('completions', lazy=True, cascade='all, delete-orphan'))


class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade='all, delete-orphan'))


class Certificate(db.Model):
    __tablename__ = 'certificate'
    id = db.Column(db.Integer, primary_key=True)
    certificate_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False, index=True)
    final_grade = db.Column(db.Float, nullable=False)
    issued_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='uq_student_course_certificate'),)
    student = db.relationship('User', backref=db.backref('certificates', lazy=True, cascade='all, delete-orphan'))
    course = db.relationship('Course', backref=db.backref('certificates', lazy=True, cascade='all, delete-orphan'))


class Discussion(db.Model):
    __tablename__ = 'discussions'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='Discussion')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    course_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, nullable=False)
    
    course = db.relationship('Course', foreign_keys=[course_id], lazy=True)
    author = db.relationship('User', foreign_keys=[user_id], lazy=True)

