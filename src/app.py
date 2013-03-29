import datetime
import os
import time
import urllib

import boto
import boto.s3
from boto.s3.key import Key
import dateutil.parser
from flask import Flask, request, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
import pytz

import config

app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

boto_conn = boto.connect_s3(os.environ['AWS_ACCESS_KEY_ID'],
                            os.environ['AWS_SECRET_ACCESS_KEY'])
boto_bucket = boto_conn.get_bucket(os.environ['S3_BUCKET_NAME'])


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(500))
    username = db.Column(db.String(100))
    password = db.Column(db.String(256))

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


# @app.route('/issues')
# def get_issues():
#     issues = Issue.query().order(-Issue.time).fetch(40)
#     return jsonify([ndb_model_to_dict(issue) for issue in issues])



class IssueHandler(BaseHandler):
    def get(self, id):
        issue = Issue.get_by_id(long(id))
        if issue is None:
            self.json_out(None)
            return

        issue_dict = ndb_model_to_dict(issue)

        reporter = User.get_by_id(issue.reporter.id())
        issue_dict['reporter'] = ndb_model_to_dict(reporter)

        comments = Comment.query(Comment.issue == issue.key)
        issue_dict['comments'] = [ndb_model_to_dict(comment)
                                  for comment in comments]

        self.json_out(issue_dict)


class AddIssueHandler(BaseHandler):
    def get(self):
        self.out("""
        <form method="post" enctype="multipart/form-data">
        <input type="hidden" name="user" value="0" />
        <input type="text" name="title" placeholder="Title" />
        <input type="datetime" name="time" placeholder="Time" />

        <input type="file" name="pictures[]" multiple />
        <textarea name="description"></textarea>
        <input type="submit" value="Submit" />
        </form>
        """)

    def post(self):
        user = User.get_or_insert(self.request.get("user"))

        pictures = []
        picture_input = self.request.POST.getall("pictures[]")
        picture_input = [] if picture_input == "" else picture_input

        for picture in picture_input:
            if not hasattr(picture, 'file'):
                continue

            filename = files.blobstore.create(mime_type=picture.type)

            with files.open(filename, 'a') as f:
                f.write(picture.value)
            files.finalize(filename)

            pictures.append(files.blobstore.get_blob_key(filename))

        date = dateutil.parser.parse(self.request.get("time"))
        date = date.astimezone(pytz.utc).replace(tzinfo=None)

        issue = Issue(reporter=user.key,
                      title=self.request.get("title"),
                      time=date,
                      description=self.request.get("description"),
                      urgency=int(self.request.get("urgency", 0)),
                      pictures=pictures)

        issue.put()


class ViewBlobHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        self.send_blob(blob_info)


SIMPLE_TYPES = (int, long, float, bool, dict, basestring, list)

def ndb_model_to_dict(model):
    output = {'key': str(model.key.id())}

    for key, prop in model._properties.iteritems():
        value = getattr(model, key)

        # Convert BlobKey list to string list
        if ( isinstance(value, list) and len(value) > 0
             and isinstance(value[0], datastore_types.BlobKey) ):
            value = map(blobkey_to_url, value)

        if value is None or isinstance(value, SIMPLE_TYPES):
            output[key] = value
        elif isinstance(value, datetime.date):
            # Convert date/datetime to ms-since-epoch ("new Date()").
            ms = time.mktime(value.utctimetuple())
            ms += getattr(value, 'microseconds', 0) / 1000
            output[key] = int(ms)
        elif isinstance(value, ndb.GeoPt):
            output[key] = {'lat': value.lat, 'lon': value.lon}
        elif isinstance(value, ndb.Key):
            output[key] = value.id()
        elif isinstance(value, ndb.BlobKeyProperty):
            output[key] = value.id()
        else:
            raise ValueError('cannot encode ' + repr(prop))

    return output



def blobkey_to_url(blobkey):
    return config.SITE_URL + 'blobs/' + str(blobkey)
