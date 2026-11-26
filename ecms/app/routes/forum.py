from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Assignment, Course, Discussion, Enrollment, Notification, Submission

forum_bp = Blueprint("forum", __name__, url_prefix="/forum")


def _student_nav_context(user):
    try:
        enrolled_course_ids = [
            e.course_id
            for e in Enrollment.query.filter_by(student_id=user.id).all()
            if getattr(e, "course_id", None) is not None
        ]
        pending_count = 0
        if enrolled_course_ids:
            assignments = Assignment.query.filter(
                Assignment.course_id.in_(enrolled_course_ids)
            ).all()
            submitted_ids = {
                s.assignment_id
                for s in Submission.query.filter_by(student_id=user.id).all()
            }
            pending_count = sum(1 for a in assignments if a.id not in submitted_ids)

        unread_count = Notification.query.filter_by(
            user_id=user.id, is_read=False
        ).count()
        return {
            "student_nav_pending": pending_count,
            "student_nav_unread": unread_count,
        }
    except Exception:
        return {"student_nav_pending": 0, "student_nav_unread": 0}


def _teacher_nav_context(user):
    try:
        ungraded = (
            Submission.query.join(Assignment)
            .join(Course)
            .filter(Course.teacher_id == user.id, Submission.grade.is_(None))
            .count()
        )
        unread = Notification.query.filter_by(
            user_id=user.id, is_read=False
        ).count()
        return {"nav_ungraded": ungraded, "nav_notifications": unread}
    except Exception:
        return {"nav_ungraded": 0, "nav_notifications": 0}


@forum_bp.route("/")
@login_required
def index():
    query = (request.args.get("q") or "").strip().lower()
    course_id = request.args.get("course")
    topic_type = request.args.get("type")

    role = (getattr(current_user, "role", "") or "").lower()

    # جلب الكورسات المتاحة للمستخدم
    courses = []
    try:
        if role == "teacher":
            courses = Course.query.filter_by(teacher_id=current_user.id).all()
        elif role == "admin":
            courses = Course.query.all()
        else:
            courses = [
                e.course
                for e in getattr(current_user, "enrollments", [])
                if getattr(e, "course", None)
            ]
    except Exception:
        courses = []

    # جلب جميع المواضيع لتظهر للجميع (طالب، مدرس، أدمن) مع دعم البحث والفلترة
    topics = []
    try:
        q = Discussion.query
        if course_id and str(course_id).isdigit():
            q = q.filter_by(course_id=int(course_id))
        if topic_type:
            q = q.filter_by(category=topic_type)
        if query:
            q = q.filter(
                Discussion.title.ilike(f"%{query}%")
                | Discussion.content.ilike(f"%{query}%")
            )
        topics = q.order_by(Discussion.created_at.desc()).all()
    except Exception:
        topics = []

    extra_ctx = {"active_page": "discussions"}
    if role == "teacher":
        extra_ctx.update(_teacher_nav_context(current_user))
        extra_ctx["teacher"] = current_user
    elif role == "student":
        extra_ctx.update(_student_nav_context(current_user))
        extra_ctx["student"] = current_user

    return render_template(
        "forum/index.html",
        courses=courses,
        topics=topics,
        **extra_ctx,
    )


@forum_bp.route("/new", methods=["GET", "POST"])
@forum_bp.route("/create", methods=["POST"])
@login_required
def new_topic():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        course_id_raw = request.form.get("course_id")
        course_id = (
            int(course_id_raw)
            if course_id_raw and str(course_id_raw).isdigit()
            else None
        )
        category = (request.form.get("category") or "Discussion").strip()

        if not title or not content:
            flash("يرجى إدخال عنوان وتفاصيل المناقشة.", "danger")
            return redirect(url_for("forum.index"))

        try:
            new_item = Discussion(
                title=title,
                content=content,
                category=category,
                course_id=course_id,
                user_id=current_user.id,
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(new_item)
            db.session.commit()
            flash("تم نشر المناقشة بنجاح!", "success")
        except Exception as exc:
            db.session.rollback()
            flash(f"حدث خطأ أثناء النشر: {str(exc)}", "danger")

        return redirect(url_for("forum.index"))

    return redirect(url_for("forum.index"))


# مسار تعديل المنشور
@forum_bp.route("/edit/<int:topic_id>", methods=["POST"])
@login_required
def edit_topic(topic_id):
    topic = Discussion.query.get_or_404(topic_id)

    is_owner = topic.user_id == current_user.id
    is_privileged = (getattr(current_user, "role", "") or "").lower() in [
        "teacher",
        "admin",
    ]
    if not (is_owner or is_privileged):
        flash("غير مصرح لك بتعديل هذه المناقشة.", "danger")
        return redirect(url_for("forum.index"))

    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    category = (request.form.get("category") or topic.category).strip()
    course_id_raw = request.form.get("course_id")

    if not title or not content:
        flash("العنوان والمحتوى مطلوبان.", "danger")
        return redirect(url_for("forum.index"))

    try:
        topic.title = title
        topic.content = content
        topic.category = category
        if course_id_raw and str(course_id_raw).isdigit():
            topic.course_id = int(course_id_raw)
        elif course_id_raw == "":
            topic.course_id = None

        db.session.commit()
        flash("تم تعديل المناقشة بنجاح!", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"تعذر حفظ التعديلات: {str(exc)}", "danger")

    return redirect(url_for("forum.index"))


# مسار حذف المنشور
@forum_bp.route("/delete/<int:topic_id>", methods=["POST"])
@login_required
def delete_topic(topic_id):
    topic = Discussion.query.get_or_404(topic_id)

    is_owner = topic.user_id == current_user.id
    is_privileged = (getattr(current_user, "role", "") or "").lower() in [
        "teacher",
        "admin",
    ]
    if not (is_owner or is_privileged):
        flash("غير مصرح لك بحذف هذه المناقشة.", "danger")
        return redirect(url_for("forum.index"))

    try:
        db.session.delete(topic)
        db.session.commit()
        flash("تم حذف المناقشة بنجاح.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"تعذر الحذف: {str(exc)}", "danger")

    return redirect(url_for("forum.index"))
