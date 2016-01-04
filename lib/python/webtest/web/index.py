#!/usr/bin/env python

from twisted.web import resource
from twisted.web import server


from webtest import log

logger = log.get_logger()


class Root(resource.Resource):

    def render_GET(self, request):
        logger.error("render_GET")
        session = request.getSession()
        logger.error("SESSION: %s" % (sorted(dir(session))),)
        return '<html><body>Hello World</body></html>'

    def eb(self, f):
        logger.error(f.getBriefTraceback())
        return f

    def getChild(self, name, request):
        logger.error("getChild: %s path:%s  uri:%s   responseHeaders:%s" % (name, request.path, request.uri, request.responseHeaders,))
        return self


