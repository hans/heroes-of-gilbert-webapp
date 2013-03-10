import dateutil

from webapp2 import WSGIApplication

from models import Issue
from base_handler import BaseHandler
import config


class IssuesHandler(BaseHandler):
    def get(self):
        issues = Issue.query().order(-Issue.time).fetch(40)
        self.json_out([issues.to_dict() for issue in issues])

class AddIssueHandler(BaseHandler):
    def get(self):
        self.out("""
        <form method="post" enctype="multipart/form-data">
        <input type="text" name="title" placeholder="Title" />
        <input type="datetime" name="time" placeholder="Time" />

        <input type="file" name="pictures[]" multiple />
        <textarea name="Description"></textarea>
        </form>
        """)

    def post(self):
        data = json.loads(self.get("issue"))

        data['time'] = dateutil.parse(data['time'])

        pictures = [db.Blob(x) for x in self.get("pictures")]
        data['pictures'] = pictures

        issue = Issue(**data)
        issue.put()


app = WSGIApplication([
    ('/issues', IssuesHandler),
    ('/issues/add', AddIssueHandler)
], debug=config.DEV)
