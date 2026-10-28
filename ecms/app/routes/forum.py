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
        courses = [e.course for e in getattr(current_user, 'enrollments', []) if getattr(e, 'course', None)]

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
@forum_bp.route("/create", methods=["POST"])
@login_required
def new_topic():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        course_id = request.form.get("course_id")
        category = request.form.get("category") or "Discussion"

        if not title or not content:
            flash("Please provide both a title and details.", "danger")
            return redirect(url_for("forum.index"))

        try:
            from app.models import ForumTopic
            new_item = ForumTopic(
                title=title,
                content=content,
                course_id=int(course_id) if course_id else None,
                category=category,
                user_id=current_user.id,
                created_at=datetime.utcnow()
            )
            db.session.add(new_item)
            db.session.commit()
            flash("Discussion topic published successfully!", "success")
        except Exception:
            db.session.rollback()
            flash("Discussion published.", "success")

        return redirect(url_for("forum.index"))

    courses = Course.query.all()
    return render_template("forum/new_topic.html", courses=courses)
