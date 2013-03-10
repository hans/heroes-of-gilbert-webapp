from webapp2 import WSGIApplication

from models import Issue
from base_handler import BaseHandler
import config


class IssuesHandler(BaseHandler):
    def get(self):
        issues = Issue.query().order(-Issue.time).fetch(40)
        self.json_out([issues.to_dict() for issue in issues])

class AddIssueHandler(BaseHandler):
    def post(self):
        data = json.loads(self.get("issue"))
        issue = Issue(**data)


app = WSGIApplication([
    ('/issues', IssuesHandler),
    ('/issues/add', AddIssueHandler)
], debug=config.DEV)
