#!/usr/bin/env python

from twisted.web.server import Request
from webtest import log

logger = log.get_logger()

def logging_errback(f, label="logging_errback"):
    logger.error("%s: %s" % (label, f.getBriefTraceback()))

class RedisRequest(Request):
    def session_callback(self, session, cookiename):
        self.session = session
        self.addCookie(cookiename, self.session.uid, path=b'/')
        self.session.touch()
        return self.session

    def getSession(self, sessionInterface=None):
        # Session management
        if not self.session:
            cookiename = b"_".join([b'TWISTED_SESSION'] + self.sitepath)
            sessionCookie = self.getCookie(cookiename)
            if sessionCookie:
                try:
                    df = self.site.getSession(sessionCookie)
                    df.addCallback(self.session_callback, cookiename)
                    df.addErrback(logging_errback, "RedisRequest.site.getSession")
                    return df
                except KeyError:
                    pass
            # if it still hasn't been set, fix it up.
            if not self.session:
                df = self.site.makeSession()
                df.addCallback(self.session_callback, cookiename)
                df.addErrback(logging_errback, "RedisRequest.site.makeSession")
                return df

        return self.session
