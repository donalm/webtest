#!/usr/bin/env python

from twisted.web import resource
from twisted.web import server


from webtest import log

logger = log.get_logger()


class Root(resource.Resource):

    def _render_GET(self, request):
        logger.error("render_GET")
        session = request.getSession()
        logger.error("SESSION: %s" % (sorted(dir(session))),)
        return '<html><body>Hello World</body></html>'

    def render_GET(self, request):
        df = request.igetSession()
        df.addCallback(self.cb, request)
        df.addErrback(self.eb)
        return server.NOT_DONE_YET

    def cb(self, session, request):
        someval = session.get("SOMEVAL", 'xxx')
        someval2 = session.get("SOMEVAL2", -1)
        session['SOMEVAL2'] = someval2 + 1

        logger.error("C: session: %s" % (session,))
        logger.error("C: someval: %s" % (someval,))

        request.write("<html>Hello, world 2!: %s  '%s' %s</html>" % (session.uid, session, request.path,))
        session['SOMEVAL'] = "HELP"
        request.finish()

    def eb(self, f):
        logger.error("index.Root: %s", f.getBriefTraceback())
        return f

    def getChild(self, name, request):
        logger.error("getChild: %s path:%s  uri:%s   responseHeaders:%s" % (name, request.path, request.uri, request.responseHeaders,))
        return self


class Simple(resource.Resource):
    isLeaf = True

