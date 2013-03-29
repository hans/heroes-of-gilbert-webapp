from app import db

class Issue(db.Model):
    reporter = ndb.KeyProperty(kind=User, required=True)
    location = ndb.GeoPtProperty()

    title = ndb.StringProperty(required=True)
    time = ndb.DateTimeProperty(required=True)
    description = ndb.TextProperty()
    urgency = ndb.IntegerProperty()
    pictures = ndb.BlobKeyProperty(repeated=True)


class Comment(ndb.Model):
    issue = ndb.KeyProperty(kind=Issue)
    author = ndb.KeyProperty(kind=User)

    time = ndb.DateTimeProperty()
    text = ndb.TextProperty()
