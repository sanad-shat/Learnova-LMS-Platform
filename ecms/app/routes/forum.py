from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Course, User, Discussion
from datetime import datetime, timezone

forum_bp = Blueprint("forum", __name__, url_prefix="/forum")

@forum_bp.route("/")
@login_required
def index():
    query = (request.args.get("q") or "").strip().lower()
    course_id = request.args.get("course")
    topic_type = request.args.get("type")

    # مساقات المدرس أو الطالب
    if getattr(current_user, 'role', '').lower() == 'teacher':
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
    else:
        courses = [e.course for e in getattr(current_user, 'enrollments', []) if getattr(e, 'course', None)]

    topics = []
    try:
        q = Discussion.query
        if course_id and str(course_id).isdigit():
            q = q.filter_by(course_id=int(course_id))
        if topic_type:
            q = q.filter_by(category=topic_type)
        if query:
            q = q.filter(Discussion.title.ilike(f"%{query}%") | Discussion.content.ilike(f"%{query}%"))
        topics = q.order_by(Discussion.created_at.desc()).all()
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
        course_id_raw = request.form.get("course_id")
        course_id = int(course_id_raw) if course_id_raw and str(course_id_raw).isdigit() else None
        category = request.form.get("category") or "Discussion"

        if not title or not content:
            flash("Please provide both a title and details for your discussion.", "danger")
            return redirect(url_for("forum.index"))

        try:
            new_item = Discussion(
                title=title,
                content=content,
                category=category,
                course_id=course_id,
                user_id=current_user.id,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(new_item)
            db.session.commit()
            flash("Discussion topic published successfully!", "success")
        except Exception as exc:
            db.session.rollback()
            flash(f"Error saving discussion: {str(exc)}", "danger")

        return redirect(url_for("forum.index"))

    return redirect(url_for("forum.index"))
