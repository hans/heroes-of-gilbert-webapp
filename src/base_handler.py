import json
import webapp2

class BaseHandler(webapp2.RequestHandler):
    """Contains convenience and other methods that we generally want access to across all handlers."""

    def __init__(self, request, response):
        super(BaseHandler, self).__init__(request, response)

    def out(self, data):
        self.response.write(data)

    def json_out(self, data, allow_jsonp=True, pretty=True):
        """
        Convenience method for JSON output.
        """
        self.response.headers['Content-Type'] = 'application/json'

        indent = 4 if pretty is True else None
        data = json.dumps(data, indent=indent)
        if allow_jsonp and self.request.get("callback"):
            data = "%s(%s)" % (self.request.get("callback"), data)

        self.out(data)
