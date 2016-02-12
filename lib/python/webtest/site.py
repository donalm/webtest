#!/usr/bin/env python

from twisted.web.server import Site
from webtest.session import RedisSessionFactory
from webtest.request import RedisRequest
from webtest import log

logger = log.get_logger()

class RedisSite(Site):
    sessionFactory = RedisSessionFactory
    requestFactory = RedisRequest

    def makeSession(self):
        """
        Generate a new Session instance
        """
        uid = self._mkuid()
        return self.sessionFactory.retrieve(uid, reactor=self._reactor)

    def getSession(self, uid):
        """
        Get a previously generated session, by its unique ID.
        This raises a KeyError if the session is not found.
        """
        return self.sessionFactory.retrieve(uid, reactor=self._reactor)


