from google.appengine.ext import ndb


class User(ndb.Model):
    email = ndb.StringProperty()
    username = ndb.StringProperty()
    password = ndb.StringProperty()


class Issue(ndb.Model):
    reporter = ndb.KeyProperty(kind=User, required=True)
    location = ndb.GeoPtProperty()

    title = ndb.StringProperty(required=True)
    time = ndb.DateTimeProperty(required=True)
    description = ndb.TextProperty()
    urgency = ndb.IntegerProperty()
    pictures = ndb.BlobProperty(repeated=True)


class Comment(ndb.Model):
    issue = ndb.KeyProperty(kind=Issue)
    author = ndb.KeyProperty(kind=User)

    time = ndb.TimeProperty()
    text = ndb.TextProperty()
