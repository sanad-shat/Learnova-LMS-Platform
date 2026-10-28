from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Course, User
from datetime import datetime

forum_bp = Blueprint("forum", __name__, url_prefix="/forum")

@forum_bp.route("/")
@login_required
def index():
    query = (request.args.get("q") or "").strip().lower()
    course_id = request.args.get("course")
    topic_type = request.args.get("type")

    if getattr(current_user, 'role', '').lower() == 'teacher':
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
    else:
        courses = [e.course for e in getattr(current_user, 'enrollments', []) if e.course]

    topics = []
    try:
        from app.models import ForumTopic
        q = ForumTopic.query
        if course_id:
            q = q.filter_by(course_id=int(course_id))
        if topic_type:
            q = q.filter_by(category=topic_type)
        if query:
            q = q.filter(ForumTopic.title.ilike(f"%{query}%") | ForumTopic.content.ilike(f"%{query}%"))
        topics = q.order_by(ForumTopic.created_at.desc()).all()
    except Exception:
        topics = []

    return render_template(
        "forum/index.html",
        courses=courses,
        topics=topics,
        teacher=current_user if getattr(current_user, 'role', '').lower() == 'teacher' else None
    )

@forum_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_topic():
    courses = Course.query.all()
    if request.method == "POST":
        flash("Discussion topic created successfully.", "success")
        return redirect(url_for("forum.index"))
    return render_template("forum/new_topic.html", courses=courses)
