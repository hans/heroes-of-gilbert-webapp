import os

NAMESPACE = 'dev'

DEV = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')
