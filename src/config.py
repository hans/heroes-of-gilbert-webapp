import os

NAMESPACE = 'dev'
DEV = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

SITE_URL = 'http://heroes-of-gilbert.appspot.com/' if not DEV else 'http://localhost:8080/'
