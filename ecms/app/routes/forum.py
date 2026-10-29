from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Course, User, Discussion
from datetime import datetime

forum_bp = Blueprint("forum", __name__, url_prefix="/forum")

@forum_bp.route("/")
@login_required
def index():
    query = (request.args.get("q") or "").strip().lower()
    course_id = request.args.get("course")
    topic_type = request.args.get("type")

    # جلب الكورسات
    if getattr(current_user, 'role', '').lower() == 'teacher':
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
    else:
        courses = [e.course for e in getattr(current_user, 'enrollments', []) if getattr(e, 'course', None)]

    topics = []
    try:
        q = Discussion.query
        if course_id and course_id.isdigit() and hasattr(Discussion, 'course_id'):
            q = q.filter_by(course_id=int(course_id))
        if topic_type:
            if hasattr(Discussion, 'category'):
                q = q.filter_by(category=topic_type)
            elif hasattr(Discussion, 'type'):
                q = q.filter_by(type=topic_type)
        if query:
            q = q.filter(Discussion.title.ilike(f"%{query}%"))
        
        # الترتيب حسب المتوفر
        if hasattr(Discussion, 'created_at'):
            topics = q.order_by(Discussion.created_at.desc()).all()
        else:
            topics = q.order_by(Discussion.id.desc()).all()
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
        course_id = int(course_id_raw) if course_id_raw and course_id_raw.isdigit() else None
        category = request.form.get("category") or "Discussion"

        if not title or not content:
            flash("Please provide both a title and details.", "danger")
            return redirect(url_for("forum.index"))

        try:
            item_kwargs = {"title": title}
            
            # فحص حقل النص
            if hasattr(Discussion, 'content'):
                item_kwargs['content'] = content
            elif hasattr(Discussion, 'body'):
                item_kwargs['body'] = content
            elif hasattr(Discussion, 'message'):
                item_kwargs['message'] = content

            # فحص حقل الكورس
            if hasattr(Discussion, 'course_id'):
                item_kwargs['course_id'] = course_id

            # فحص الفئة
            if hasattr(Discussion, 'category'):
                item_kwargs['category'] = category
            elif hasattr(Discussion, 'type'):
                item_kwargs['type'] = category

            # فحص حقل صاحب المنشور
            if hasattr(Discussion, 'user_id'):
                item_kwargs['user_id'] = current_user.id
            elif hasattr(Discussion, 'author_id'):
                item_kwargs['author_id'] = current_user.id
            elif hasattr(Discussion, 'teacher_id'):
                item_kwargs['teacher_id'] = current_user.id

            if hasattr(Discussion, 'created_at'):
                item_kwargs['created_at'] = datetime.utcnow()

            new_item = Discussion(**item_kwargs)
            db.session.add(new_item)
            db.session.commit()
            flash("Discussion topic published successfully!", "success")
        except Exception as exc:
            db.session.rollback()
            flash(f"Error publishing: {str(exc)}", "danger")

        return redirect(url_for("forum.index"))

    return redirect(url_for("forum.index"))
