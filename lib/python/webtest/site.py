#!/usr/bin/env python

from twisted.web.server import Site
from twisted.web.server import Request
from webtest.session import RedisSessionFactory
from webtest import log

logger = log.get_logger()

def eb(f, label="EB2"):
    logger.error("%s: %s", label, f.getBriefTraceback())

class RedisRequest(Request):
    def session_callback(self, session, cookiename):
        self.session = session
        self.addCookie(cookiename, self.session.uid, path=b'/')
        self.session.touch()
        return self.session

    def igetSession(self, sessionInterface=None):
        # Session management
        logger.error("getSession")
        if not self.session:
            cookiename = b"_".join([b'TWISTED_SESSION'] + self.sitepath)
            sessionCookie = self.getCookie(cookiename)
            logger.error("X1: %s" % (sessionCookie,))
            if sessionCookie:
                try:
                    df = self.site.getSession(sessionCookie)
                    df.addCallback(self.session_callback, cookiename)
                    df.addErrback(eb, "get  session")
                    return df
                except KeyError:
                    pass
            logger.error("X2")
            # if it still hasn't been set, fix it up.
            if not self.session:
                df = self.site.makeSession()
                df.addCallback(self.session_callback, cookiename)
                df.addErrback(eb, "make session")
                return df

        #if sessionInterface:
        #    return self.session.getComponent(sessionInterface)
        return self.session

class RedisSite(Site):
    sessionFactory = RedisSessionFactory
    requestFactory = RedisRequest

    def makeSession(self):
        """
        Generate a new Session instance, and store it for future reference.
        """
        uid = self._mkuid()
        logger.error("makeSession: %s" % (uid,))
        """
        Should we even keep sessions in self.sessions?
        """
        return self.sessionFactory.retrieve(uid, reactor=self._reactor)

    def getSession(self, uid):
        """
        Get a previously generated session, by its unique ID.
        This raises a KeyError if the session is not found.
        """
        """
        Here we should run out to persistent session storage
        to see if there's data there
        """
        logger.error("site.getSession")
        return self.sessionFactory.retrieve(uid, reactor=self._reactor)


