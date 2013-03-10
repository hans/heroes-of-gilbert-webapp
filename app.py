from webapp2 import WSGIApplication

from models import Issue
from base_handler import BaseHandler
import config


class IssuesHandler(BaseHandler):
    def get(self):
        issues = Issue.query().order(-Issue.time).fetch(40)
        self.json_out([issues.to_dict() for issue in issues])





app = WSGIApplication([
    ('/issues', IssuesHandler),
], debug=config.DEV)
