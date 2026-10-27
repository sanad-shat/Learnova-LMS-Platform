from pathlib import Path
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Course, Enrollment, DiscussionTopic, DiscussionPost, DiscussionLike, Notification
from app.services import notify_course_students

forum_bp = Blueprint('forum', __name__, url_prefix='/forum')
UPLOAD_DIR = Path(__file__).resolve().parents[1] / 'static' / 'forum_uploads'
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass
ALLOWED = {'pdf','doc','docx','ppt','pptx','png','jpg','jpeg','zip','txt'}

def _save_file(file):
    if not file or not file.filename:
        return None
    name = secure_filename(file.filename)
    if '.' not in name or name.rsplit('.',1)[1].lower() not in ALLOWED:
        return None
    final = f"{uuid.uuid4().hex}_{name}"
    file.save(UPLOAD_DIR / final)
    return final

def _courses():
    if current_user.role == 'admin': return Course.query.order_by(Course.name).all()
    if current_user.role == 'teacher': return Course.query.filter_by(teacher_id=current_user.id).order_by(Course.name).all()
    return [e.course for e in current_user.enrollments]

def _allowed(course):
    return current_user.role == 'admin' or (current_user.role == 'teacher' and course.teacher_id == current_user.id) or Enrollment.query.filter_by(student_id=current_user.id, course_id=course.id).first() is not None

def _moderator(topic):
    return current_user.role == 'admin' or (current_user.role == 'teacher' and topic.course.teacher_id == current_user.id)

@forum_bp.route('/')
@login_required
def index():
    courses=_courses(); ids=[c.id for c in courses]; q=request.args.get('q','').strip(); course_id=request.args.get('course_id',type=int); topic_type=request.args.get('type','').strip()
    query=DiscussionTopic.query.filter(DiscussionTopic.course_id.in_(ids or [-1]))
    if course_id in ids: query=query.filter_by(course_id=course_id)
    if topic_type: query=query.filter_by(topic_type=topic_type)
    if q: query=query.filter(db.or_(DiscussionTopic.title.ilike(f'%{q}%'),DiscussionTopic.body.ilike(f'%{q}%')))
    topics=query.order_by(DiscussionTopic.is_pinned.desc(),DiscussionTopic.updated_at.desc()).all()
    return render_template('forum/index.html',courses=courses,topics=topics,query=q,selected_course=course_id,selected_type=topic_type)

@forum_bp.route('/new',methods=['GET','POST'])
@login_required
def new_topic():
    courses=_courses()
    if request.method=='POST':
        course=Course.query.get_or_404(request.form.get('course_id',type=int))
        if not _allowed(course): flash('Access denied.','danger'); return redirect(url_for('forum.index'))
        title=request.form.get('title','').strip(); body=request.form.get('body','').strip(); t=request.form.get('topic_type','Discussion')
        if t=='Announcement' and current_user.role not in ('teacher','admin'): t='Discussion'
        if not title or not body: flash('Title and message are required.','danger')
        else:
            topic=DiscussionTopic(course_id=course.id,author_id=current_user.id,title=title,body=body,topic_type=t,attachment_path=_save_file(request.files.get('attachment')))
            db.session.add(topic); db.session.flush(); notify_course_students(course,f'New {t.lower()}',f'{current_user.name_person or current_user.username}: {title}',url_for('forum.topic',topic_id=topic.id)); db.session.commit(); flash('Topic created.','success'); return redirect(url_for('forum.topic',topic_id=topic.id))
    return render_template('forum/new_topic.html',courses=courses)

@forum_bp.route('/topic/<int:topic_id>',methods=['GET','POST'])
@login_required
def topic(topic_id):
    topic=DiscussionTopic.query.get_or_404(topic_id)
    if not _allowed(topic.course): flash('Access denied.','danger'); return redirect(url_for('forum.index'))
    if request.method=='POST':
        if topic.is_locked and not _moderator(topic): flash('This discussion is locked.','warning'); return redirect(url_for('forum.topic',topic_id=topic.id))
        body=request.form.get('body','').strip(); attachment=_save_file(request.files.get('attachment'))
        if not body and not attachment: flash('Reply or attachment is required.','danger')
        else:
            db.session.add(DiscussionPost(topic_id=topic.id,author_id=current_user.id,body=body or 'Attachment',attachment_path=attachment))
            recipients={topic.author_id,topic.course.teacher_id,*[e.student_id for e in topic.course.enrollments]}; recipients.discard(current_user.id)
            for uid in recipients: db.session.add(Notification(user_id=uid,title='New forum reply',message=f'New reply in “{topic.title}”.',link=url_for('forum.topic',topic_id=topic.id)))
            db.session.commit(); flash('Reply posted.','success'); return redirect(url_for('forum.topic',topic_id=topic.id))
    liked=DiscussionLike.query.filter_by(topic_id=topic.id,user_id=current_user.id).first() is not None
    return render_template('forum/topic.html',topic=topic,liked=liked)

@forum_bp.route('/topic/<int:topic_id>/like',methods=['POST'])
@login_required
def like_topic(topic_id):
    topic=DiscussionTopic.query.get_or_404(topic_id)
    if not _allowed(topic.course): return redirect(url_for('forum.index'))
    like=DiscussionLike.query.filter_by(topic_id=topic.id,user_id=current_user.id).first()
    if like: db.session.delete(like)
    else: db.session.add(DiscussionLike(topic_id=topic.id,user_id=current_user.id))
    db.session.commit(); return redirect(url_for('forum.topic',topic_id=topic.id))

@forum_bp.route('/topic/<int:topic_id>/edit',methods=['GET','POST'])
@login_required
def edit_topic(topic_id):
    topic=DiscussionTopic.query.get_or_404(topic_id)
    if current_user.id!=topic.author_id and not _moderator(topic): flash('You cannot edit this topic.','danger'); return redirect(url_for('forum.topic',topic_id=topic.id))
    if request.method=='POST':
        topic.title=request.form.get('title','').strip(); topic.body=request.form.get('body','').strip(); topic.topic_type=request.form.get('topic_type',topic.topic_type) if _moderator(topic) else topic.topic_type
        attachment=_save_file(request.files.get('attachment')); topic.attachment_path=attachment or topic.attachment_path; db.session.commit(); flash('Topic updated.','success'); return redirect(url_for('forum.topic',topic_id=topic.id))
    return render_template('forum/edit_topic.html',topic=topic)

@forum_bp.route('/topic/<int:topic_id>/delete',methods=['POST'])
@login_required
def delete_topic(topic_id):
    topic=DiscussionTopic.query.get_or_404(topic_id)
    if current_user.id!=topic.author_id and not _moderator(topic): flash('You cannot delete this topic.','danger')
    else: db.session.delete(topic); db.session.commit(); flash('Topic deleted.','success')
    return redirect(url_for('forum.index'))

@forum_bp.route('/topic/<int:topic_id>/moderate',methods=['POST'])
@login_required
def moderate(topic_id):
    topic=DiscussionTopic.query.get_or_404(topic_id)
    if not _moderator(topic): flash('Moderator access required.','danger'); return redirect(url_for('forum.topic',topic_id=topic.id))
    action=request.form.get('action')
    if action=='pin': topic.is_pinned=not topic.is_pinned
    elif action=='lock': topic.is_locked=not topic.is_locked
    db.session.commit(); return redirect(url_for('forum.topic',topic_id=topic.id))

@forum_bp.route('/post/<int:post_id>/delete',methods=['POST'])
@login_required
def delete_post(post_id):
    post=DiscussionPost.query.get_or_404(post_id)
    if current_user.id!=post.author_id and not _moderator(post.topic): flash('You cannot delete this reply.','danger')
    else: tid=post.topic_id; db.session.delete(post); db.session.commit(); flash('Reply deleted.','success'); return redirect(url_for('forum.topic',topic_id=tid))
    return redirect(url_for('forum.topic',topic_id=post.topic_id))
