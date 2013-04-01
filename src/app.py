from datetime import datetime
import os

import boto
import boto.s3
from boto.s3.key import Key
import dateutil.parser
from flask import Flask, request, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
import pytz


app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
boto_conn = boto.connect_s3(os.environ['AWS_ACCESS_KEY_ID'],
                            os.environ['AWS_SECRET_ACCESS_KEY'])
boto_bucket = boto_conn.get_bucket(S3_BUCKET_NAME)


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(500))
    username = db.Column(db.String(100))
    password = db.Column(db.String(256))

    @property
    def serialize(self):
        return {
            'key': self.id,
            'username': self.username
        }

    @staticmethod
    def get_or_create(session, id):
        u = session.query(User).filter_by(id=id).first()
        if u:
            return u

        u = User(id=id)
        session.add(u)
        return u


class Picture(db.Model):
    __tablename__ = 'picture'

    id = db.Column(db.Integer, primary_key=True)

    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'))
    issue = db.relationship('Issue')

    s3_name = db.Column(db.String(1024))

    @property
    def url(self):
        return 'http://{}.s3.amazonaws.com/{}'.format(S3_BUCKET_NAME,
                                                      self.s3_name)


class Comment(db.Model):
    __tablename__ = 'comment'

    id = db.Column(db.Integer, primary_key=True)

    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'))
    issue = db.relationship('Issue')

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User')

    time = db.Column(db.DateTime, nullable=False)
    text = db.Column(db.String(1000), nullable=False)

    @property
    def serialize(self):
        return {
            'key': self.id,
            'time': long(self.time.strftime('%s')),
            'issue': self.issue_id,
            'author': self.author.serialize,
            'text': self.text
        }


class Issue(db.Model):
    __tablename__ = 'issue'

    id = db.Column(db.Integer, primary_key=True)

    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reporter = db.relationship('User')

    location_lat = db.Column(db.Float)
    location_lon = db.Column(db.Float)

    title = db.Column(db.String(200), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(1000))
    urgency = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, default=0)

    @property
    def pictures(self):
        return db.session.query(Picture).filter(Picture.issue==self).all()

    @property
    def comments(self):
        return db.session.query(Comment).filter(Comment.issue==self).all()

    @property
    def serialize(self):
        picture_urls = [p.url for p in self.pictures]

        location = None
        if self.location_lat and self.location_lon:
            location = {'lat': self.location_lat, 'lon': self.location_lon}

        ret = {
            'key': self.id,
            'reporter': self.reporter_id,
            'pictures': picture_urls,
            'title': self.title,
            'description': self.description,
            'location': location,
            'time': long(self.time.strftime('%s')),
            'urgency': int(self.urgency),
            'status': int(self.status)
        }

        return ret

    @property
    def serialize_detailed(self):
        s = self.serialize

        u = db.session.query(User).filter(User.id==s['reporter']).first()
        s['reporter'] = u.serialize if u else None

        s['comments'] = [c.serialize for c in self.comments]

        return s


@app.route('/issues')
def get_issues():
    issues = db.session.query(Issue).order_by(Issue.time).limit(40).all()
    return jsonify({'issues': [i.serialize for i in issues]})


@app.route('/issues/<int:issue_id>')
def get_issue(issue_id):
    i = db.session.query(Issue).filter(Issue.id == issue_id).first()
    if i:
        return jsonify({'issue': i.serialize_detailed})
    return jsonify({})


@app.route('/issues/add', methods=['GET', 'POST'])
def add_issue():
    if request.method == 'POST':
        u = User.get_or_create(db.session, int(request.form['user']))

        date = dateutil.parser.parse(request.form['time'])
        date = date.astimezone(pytz.utc).replace(tzinfo=None)

        issue = Issue(reporter=u,
                      title=request.form['title'],
                      time=date,
                      description=request.form['description'],
                      urgency=int(request.form.get('urgency', 0)))

        db.session.add(issue)
        db.session.commit()

        pictures = request.files.getlist("pictures[]")
        # TODO: check extension

        for picture in pictures:
            k = Key(boto_bucket)
            k.set_contents_from_file(picture.stream)
            k.make_public()

            p = Picture(issue=issue, s3_name=k.name)
            db.session.add(p)
        db.session.commit()

        return ""
    else:
        return """
        <form method="post" enctype="multipart/form-data">
        <input type="hidden" name="user" value="0" />
        <input type="text" name="title" placeholder="Title" />
        <input type="datetime" name="time" placeholder="Time" />

        <input type="file" name="pictures[]" multiple />
        <textarea name="description"></textarea>
        <input type="submit" value="Submit" />
        </form>
        """


@app.route('/issues/<int:issue_id>/comment/add', methods=['GET', 'POST'])
def add_comment(issue_id):
    if request.method == 'POST':
        u = User.get_or_create(db.session, int(request.form['author']))

        c = Comment(issue_id=issue_id,
                    author=u,
                    time=datetime.now(),
                    text=request.form['text'])
        db.session.add(c)
        db.session.commit()

        return ""
    else:
        return """
        <form method="post">
        <input type="hidden" name="author" value="0" />
        <textarea name="text"></textarea>
        <input type="submit" value="Submit" />
        </form>
        """


@app.route('/issues/<int:issue_id>/status', methods=['POST'])
def issue_status(issue_id):
    if request.method == 'POST':
        i = ( db.session.query(Issue)
              .filter(Issue.id == issue_id)
              .first() )

        if i == None:
            return "florp", 404

        status = int(request.form['status'])
        i.status = status

        db.session.commit()
        return ""


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
