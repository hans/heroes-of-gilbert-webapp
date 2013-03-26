import datetime
import time
import urllib

import dateutil.parser
from google.appengine.api import datastore_types, files
from google.appengine.ext import blobstore, ndb
from google.appengine.ext.webapp import blobstore_handlers
import pytz
from webapp2 import WSGIApplication

from models import Comment, Issue, User
from base_handler import BaseHandler
import config


class IssuesHandler(BaseHandler):
    def get(self):
        issues = Issue.query().order(-Issue.time).fetch(40)
        self.json_out([ndb_model_to_dict(issue) for issue in issues])


class IssueHandler(BaseHandler):
    def get(self, id):
        issue = Issue.get_by_id(long(id))
        if issue is None:
            self.json_out(None)
            return

        issue_dict = ndb_model_to_dict(issue)

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


app = WSGIApplication([
    (r'/issues', IssuesHandler),
    (r'/issues/([\d]+)', IssueHandler),
    (r'/issues/add', AddIssueHandler),
    (r'/blobs/([\w\-_]+)', ViewBlobHandler)
], debug=config.DEV)
