#!/usr/bin/env python

from twisted.web.server import Site
from webtest.session_dict import PersistentSessionDict
from twisted.internet import defer
from twisted.internet import reactor
from twisted.trial import unittest

class DummySessionFactory(object):
    _data = {}
    _reactor = None

    @classmethod
    def retrieve(cls, uid, reactor):
        session_data = cls._data.get(uid, dict())
        return PersistentSessionDict(uid, session_data, cls, reactor)

    @classmethod
    def delete_keys_from_session(cls, uid, keys):
        payload = cls._data.get(setdefault, dict())
        for key in keys:
            if key in payload:
                payload.pop(key)
        return cls.df()

    @classmethod
    def df():
        df = defer.Deferred()
        df.callback("OK")
        return df

    @classmethod
    def expire(cls, uid):
        cls._data.pop(uid)
        return cls.df()

    @classmethod
    def patch_session(cls, uid, patch):
        payload = cls._data.setdefault(uid, dict())
        payload.update(patch)
        return cls.df()

    @classmethod
    def touch_session(cls, uid, timeout):
        return cls.df()


class SessionTests(unittest.TestCase):
    """
    Tests for persistent HTTP connections.
    """
    def setUp(self):
        s = Site(None)
        self.uid = s._mkuid()
        self.dsf = DummySessionFactory()
        self.session = self.dsf.retrieve(self.uid, reactor=reactor)

    def test_setitem(self):
        df = self.session["TEST_KEY"] = "TEST_VALUE"
        def t(r):
            
