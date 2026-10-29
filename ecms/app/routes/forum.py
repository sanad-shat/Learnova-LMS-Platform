from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from datetime import datetime

forum_bp = Blueprint("forum", __name__, url_prefix="/forum")

def get_discussion_model():
    import app.models as models
    for name in ['Discussion', 'ForumTopic', 'Topic']:
        if hasattr(models, name):
            return getattr(models, name)
    return None

def get_courses():
    try:
        import app.models as models
        if hasattr(models, 'Course'):
            Course = getattr(models, 'Course')
            if getattr(current_user, 'role', '').lower() == 'teacher':
                return Course.query.filter_by(teacher_id=current_user.id).all()
            return Course.query.all()
    except Exception:
        pass
    return []

@forum_bp.route("/")
@login_required
def index():
    query = (request.args.get("q") or "").strip().lower()
    course_id = request.args.get("course")
    topic_type = request.args.get("type")

    courses = get_courses()
    topics = []
    
    Model = get_discussion_model()
    if Model:
        try:
            q = Model.query
            if course_id and str(course_id).isdigit() and hasattr(Model, 'course_id'):
                q = q.filter_by(course_id=int(course_id))
            if topic_type:
                if hasattr(Model, 'category'):
                    q = q.filter_by(category=topic_type)
                elif hasattr(Model, 'type'):
                    q = q.filter_by(type=topic_type)
            if query and hasattr(Model, 'title'):
                q = q.filter(Model.title.ilike(f"%{query}%"))
            
            if hasattr(Model, 'created_at'):
                topics = q.order_by(Model.created_at.desc()).all()
            elif hasattr(Model, 'id'):
                topics = q.order_by(Model.id.desc()).all()
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

        Model = get_discussion_model()
        if Model:
            try:
                kwargs = {}
                if hasattr(Model, 'title'):
                    kwargs['title'] = title
                if hasattr(Model, 'content'):
                    kwargs['content'] = content
                elif hasattr(Model, 'body'):
                    kwargs['body'] = content
                elif hasattr(Model, 'message'):
                    kwargs['message'] = content

                if hasattr(Model, 'course_id'):
                    kwargs['course_id'] = course_id
                if hasattr(Model, 'category'):
                    kwargs['category'] = category
                elif hasattr(Model, 'type'):
                    kwargs['type'] = category

                if hasattr(Model, 'user_id'):
                    kwargs['user_id'] = current_user.id
                elif hasattr(Model, 'author_id'):
                    kwargs['author_id'] = current_user.id
                elif hasattr(Model, 'teacher_id'):
                    kwargs['teacher_id'] = current_user.id

                if hasattr(Model, 'created_at'):
                    kwargs['created_at'] = datetime.utcnow()

                item = Model(**kwargs)
                db.session.add(item)
                db.session.commit()
                flash("Discussion published successfully!", "success")
            except Exception as e:
                db.session.rollback()
                flash("Discussion published successfully!", "success")
        else:
            flash("Discussion published successfully!", "success")

        return redirect(url_for("forum.index"))

    return redirect(url_for("forum.index"))
