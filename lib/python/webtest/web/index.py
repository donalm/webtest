#!/usr/bin/env python

from twisted.web import resource
from twisted.web import server


from webtest import log

logger = log.get_logger()


class Root(resource.Resource):

    def _render_GET(self, request):
        session = request.getSession()
        return '<html><body>Hello World</body></html>'

    def render_GET(self, request):
        df = request.getSession()
        df.addCallback(self.cb, request)
        df.addErrback(self.eb)
        return server.NOT_DONE_YET

    def cb(self, session, request):
        someval = session.get("SOMEVAL", 'xxx')
        someval2 = session.get("SOMEVAL2", -1)
        session['SOMEVAL2'] = someval2 + 1

        request.write("<html>Hello, world 2!: %s  '%s' %s</html>" % (session.uid, session, request.path,))
        session['SOMEVAL'] = "HELP"
        request.finish()

    def eb(self, f):
        logger.error("ERROR: index.Root: %s", f.getBriefTraceback())
        return f

    def getChild(self, name, request):
        return self


class Simple(resource.Resource):
    isLeaf = True

