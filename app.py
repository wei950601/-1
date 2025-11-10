from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'changeme'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tutor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------- Models ----------
class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), default="使用者名稱")
    avatar_url = db.Column(db.String(255), default="")

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    start_dt = db.Column(db.DateTime, nullable=False)
    end_dt = db.Column(db.DateTime, nullable=False)
    reminder1 = db.Column(db.String(16), nullable=True)  # '2h' or '1d' or None
    reminder2 = db.Column(db.String(16), nullable=True)

class Checkin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.Date, unique=True, nullable=False)
    checked = db.Column(db.Boolean, default=False)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=True)

class NotebookEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    the_date = db.Column(db.Date, nullable=False, default=date.today)
    content = db.Column(db.Text, default="")  # newline-separated bullets

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    the_date = db.Column(db.Date, nullable=False, default=date.today)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    rank = db.Column(db.Integer, nullable=True)
    subject = db.relationship('Subject')

# ---------- Helpers ----------
def month_calendar(year:int, month:int):
    import calendar
    cal = calendar.Calendar(firstweekday=0)
    days = list(cal.itermonthdates(year, month))
    # group into weeks
    weeks = []
    for i in range(0, len(days), 7):
        weeks.append(days[i:i+7])
    return weeks

# ---------- Routes ----------
@app.route('/')
def index():
    profile = UserProfile.query.first()
    if not profile:
        profile = UserProfile()
        db.session.add(profile)
        db.session.commit()
    return render_template('index.html', profile=profile)

@app.route('/profile', methods=['GET','POST'])
def profile():
    profile = UserProfile.query.first()
    if request.method == 'POST':
        profile.name = request.form.get('name') or profile.name
        profile.avatar_url = request.form.get('avatar_url','')
        db.session.commit()
        flash('已更新個人資料','success')
        return redirect(url_for('index'))
    return render_template('profile.html', profile=profile)

# ---- Calendar ----
@app.route('/calendar')
def calendar_page():
    now = datetime.now()
    y = int(request.args.get('y', now.year))
    m = int(request.args.get('m', now.month))
    weeks = month_calendar(y, m)
    # fetch events for the month
    start = date(y, m, 1)
    if m == 12:
        end = date(y+1, 1, 1)
    else:
        end = date(y, m+1, 1)
    events = Event.query.filter(Event.start_dt >= start, Event.start_dt < end).all()
    events_by_day = {}
    for e in events:
        d = e.start_dt.date()
        events_by_day.setdefault(d, []).append(e)
    return render_template('calendar.html', year=y, month=m, weeks=weeks, events_by_day=events_by_day)

@app.route('/calendar/add', methods=['POST'])
def add_event():
    title = request.form['title']
    start_dt = datetime.fromisoformat(request.form['start_dt'])
    end_dt = datetime.fromisoformat(request.form['end_dt'])
    reminder1 = request.form.get('reminder1') or None
    reminder2 = request.form.get('reminder2') or None
    e = Event(title=title, start_dt=start_dt, end_dt=end_dt, reminder1=reminder1, reminder2=reminder2)
    db.session.add(e)
    db.session.commit()
    flash('已新增行程','success')
    return redirect(url_for('calendar_page', y=start_dt.year, m=start_dt.month))

@app.route('/calendar/delete/<int:eid>', methods=['POST'])
def delete_event(eid):
    e = Event.query.get_or_404(eid)
    y, m = e.start_dt.year, e.start_dt.month
    db.session.delete(e)
    db.session.commit()
    flash('已刪除行程','info')
    return redirect(url_for('calendar_page', y=y, m=m))

# ---- Check-in ----
@app.route('/checkin')
def checkin_page():
    now = date.today()
    y = int(request.args.get('y', now.year))
    m = int(request.args.get('m', now.month))
    weeks = month_calendar(y, m)
    # get existing checkins in month
    start = date(y, m, 1)
    end = date(y+1, 1, 1) if m==12 else date(y, m+1, 1)
    existing = {c.day: c for c in Checkin.query.filter(Checkin.day>=start, Checkin.day<end).all()}
    return render_template('checkin.html', year=y, month=m, weeks=weeks, existing=existing, today=date.today())

@app.route('/checkin/toggle', methods=['POST'])
def checkin_toggle():
    day = date.fromisoformat(request.form['day'])
    checked = request.form.get('checked') == 'true'
    c = Checkin.query.filter_by(day=day).first()
    if not c:
        c = Checkin(day=day, checked=checked)
        db.session.add(c)
    else:
        c.checked = checked
    db.session.commit()
    return jsonify({'ok': True})

# ---- Questions ----
@app.route('/questions', methods=['GET','POST'])
def questions_page():
    if request.method == 'POST':
        text = request.form.get('text','').strip()
        if text:
            db.session.add(Question(text=text))
            db.session.commit()
            flash('已新增問題','success')
        return redirect(url_for('questions_page'))
    questions = Question.query.order_by(Question.created_at.desc()).all()
    return render_template('questions.html', questions=questions)

@app.route('/questions/answer/<int:qid>', methods=['POST'])
def questions_answer(qid):
    q = Question.query.get_or_404(qid)
    q.answer = request.form.get('answer','').strip() or None
    db.session.commit()
    flash('已更新答案','success')
    return redirect(url_for('questions_page'))

# ---- Notebook ----
@app.route('/notebook', methods=['GET','POST'])
def notebook_page():
    if request.method == 'POST':
        the_date = date.fromisoformat(request.form['the_date'])
        bullets = request.form.getlist('bullet')
        content = '\n'.join([b for b in bullets if b.strip()])
        entry = NotebookEntry.query.filter_by(the_date=the_date).first()
        if not entry:
            entry = NotebookEntry(the_date=the_date, content=content)
            db.session.add(entry)
        else:
            entry.content = content
        db.session.commit()
        flash('已儲存聯絡簿內容','success')
        return redirect(url_for('notebook_page'))
    # GET
    today = date.today()
    query_date = request.args.get('d')
    if query_date:
        cur_date = date.fromisoformat(query_date)
    else:
        cur_date = today
    entry = NotebookEntry.query.filter_by(the_date=cur_date).first()
    bullets = (entry.content.split('\n') if entry and entry.content else [''])
    return render_template('notebook.html', cur_date=cur_date, bullets=bullets)

# ---- Grades ----
@app.route('/grades', methods=['GET','POST'])
def grades_page():
    if request.method == 'POST':
        if 'new_subject' in request.form and request.form.get('new_subject').strip():
            s = Subject(name=request.form['new_subject'].strip())
            db.session.add(s)
            db.session.commit()
            flash('已新增科目','success')
            return redirect(url_for('grades_page'))
        # add grade
        the_date = date.fromisoformat(request.form['the_date'])
        subject_id = int(request.form['subject_id'])
        score = float(request.form['score'])
        rank = request.form.get('rank')
        rank = int(rank) if rank else None
        g = Grade(the_date=the_date, subject_id=subject_id, score=score, rank=rank)
        db.session.add(g)
        db.session.commit()
        flash('已新增成績','success')
        return redirect(url_for('grades_page'))
    # GET
    subjects = Subject.query.order_by(Subject.name.asc()).all()
    grades = Grade.query.order_by(Grade.the_date.desc()).all()
    return render_template('grades.html', subjects=subjects, grades=grades, today=date.today())

@app.route('/grades/delete/<int:gid>', methods=['POST'])
def grade_delete(gid):
    g = Grade.query.get_or_404(gid)
    db.session.delete(g)
    db.session.commit()
    flash('已刪除成績','info')
    return redirect(url_for('grades_page'))

# ---- Simple search (main page) ----
@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip()
    # naive mapping based on keywords
    mapping = {
        '行事曆': url_for('calendar_page'),
        '打卡': url_for('checkin_page'),
        '問題': url_for('questions_page'),
        '聯絡簿': url_for('notebook_page'),
        '成績': url_for('grades_page'),
        '成績紀錄': url_for('grades_page'),
        'profile': url_for('profile'),
        '個人': url_for('profile'),
        '頭像': url_for('profile'),
        '姓名': url_for('profile'),
    }
    results = []
    for k, v in mapping.items():
        if q and (q.lower() in k.lower() or k.lower() in q.lower()):
            results.append({'title': k, 'url': v})
    return jsonify(results)

# ---------- Init DB ----------
@app.cli.command('initdb')
def initdb():
    db.create_all()
    # default subjects
    if Subject.query.count() == 0:
        for n in ['國文','英文','數學','理化','生物','地理','歷史','公民']:
            db.session.add(Subject(name=n))
        db.session.commit()
    if not UserProfile.query.first():
        db.session.add(UserProfile())
        db.session.commit()
    print("DB initialized.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if Subject.query.count() == 0:
            for n in ['國文','英文','數學']:
                db.session.add(Subject(name=n))
            db.session.commit()
        if not UserProfile.query.first():
            db.session.add(UserProfile())
            db.session.commit()
    app.run(debug=True)
