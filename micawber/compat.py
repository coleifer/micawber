import sys

PY3 = sys.version_info >= (3,)

if PY3:
    from urllib.request import Request, urlopen, URLError, HTTPError
    from urllib.parse import urlencode
    text_type = str
else:
    from urllib2 import Request, urlopen, URLError, HTTPError
    from urllib import urlencode
    text_type = unicode
