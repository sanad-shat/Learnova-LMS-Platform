from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Course, User
from datetime import datetime

# استيراد موديل النقاشات المعتمد في المشروع تلقائياً
DiscussionModel = None
try:
    from app.models import Discussion as DiscussionModel
except ImportError:
    try:
        from app.models import ForumTopic as DiscussionModel
    except ImportError:
        try:
            from app.models import Topic as DiscussionModel
        except ImportError:
            pass

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
    if DiscussionModel:
        try:
            q = DiscussionModel.query
            if course_id:
                q = q.filter_by(course_id=int(course_id))
            if topic_type and hasattr(DiscussionModel, 'category'):
                q = q.filter_by(category=topic_type)
            if query:
                q = q.filter(DiscussionModel.title.ilike(f"%{query}%"))
            topics = q.order_by(DiscussionModel.id.desc()).all()
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

        if not DiscussionModel:
            flash("Discussion model is not configured yet in app/models.py", "warning")
            return redirect(url_for("forum.index"))

        try:
            # مطابقة الحقول بناءً على خصائص الموديل المعرف في قاعدة البيانات
            item_kwargs = {"title": title, "content": content}
            
            if hasattr(DiscussionModel, 'course_id'):
                item_kwargs['course_id'] = course_id
            if hasattr(DiscussionModel, 'category'):
                item_kwargs['category'] = category
            if hasattr(DiscussionModel, 'type'):
                item_kwargs['type'] = category
            if hasattr(DiscussionModel, 'user_id'):
                item_kwargs['user_id'] = current_user.id
            elif hasattr(DiscussionModel, 'author_id'):
                item_kwargs['author_id'] = current_user.id
            elif hasattr(DiscussionModel, 'teacher_id'):
                item_kwargs['teacher_id'] = current_user.id
            if hasattr(DiscussionModel, 'created_at'):
                item_kwargs['created_at'] = datetime.utcnow()

            new_item = DiscussionModel(**item_kwargs)
            db.session.add(new_item)
            db.session.commit()
            flash("Discussion topic published successfully!", "success")
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not publish topic: {exc}", "danger")

        return redirect(url_for("forum.index"))

    courses = Course.query.all()
    return render_template("forum/new_topic.html", courses=courses)
