#!/usr/bin/env python

import os
import exceptions
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
        someval = session.get("SOMEVAL2", -1)
        session['SOMEVAL2'] = someval + 1

        request.write("<html><pre>         PID: %05d\n Session UID: %s\nSession data: %s\nRequest path: %s</html>" % (os.getpid(), session.uid, session, request.path,))
        try:
            request.finish()
        except exceptions.RuntimeError, e:
            if e.message[0:64] == '''Request.finish called on a request after its connection was lost''':
                return
            logger.error(e)
            raise

    def eb(self, f):
        logger.error("ERROR: index.Root: %s", f.getBriefTraceback())
        return f

    def getChild(self, name, request):
        return self
