import datetime
import time

import dateutil.parser
from google.appengine.ext import ndb
from webapp2 import WSGIApplication

from models import Issue, User
from base_handler import BaseHandler
import config


class IssuesHandler(BaseHandler):
    def get(self):
        issues = Issue.query().order(-Issue.time).fetch(40)
        self.json_out([ndb_model_to_dict(issue) for issue in issues])

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

        pictures = self.request.get("pictures")
        if pictures == "":
            pictures = []

        issue = Issue(reporter=user.key,
                      title=self.request.get("title"),
                      time=dateutil.parser.parse(self.request.get("time")),
                      description=self.request.get("description"),
                      urgency=self.request.get("urgency", 0),
                      pictures=pictures)

        issue.put()


SIMPLE_TYPES = (int, long, float, bool, dict, basestring, list)

def ndb_model_to_dict(model):
    output = {'key': model.key.id()}

    for key, prop in model._properties.iteritems():
        value = getattr(model, key)

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
            output[key] = ndb_model_to_dict(value.get())
        else:
            raise ValueError('cannot encode ' + repr(prop))

    return output


app = WSGIApplication([
    ('/issues', IssuesHandler),
    ('/issues/add', AddIssueHandler)
], debug=config.DEV)