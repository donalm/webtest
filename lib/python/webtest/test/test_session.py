#!/usr/bin/env python

import time
import string
import random

from twisted.web.server import Site
from webtest.session_dict import PersistentSessionDict
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet import task
from twisted.trial import unittest
from twisted.internet import base
base.DelayedCall.debug=True

def random_string(length=12):
    return ''.join([string.ascii_letters[random.randrange(0,52)] for x in range(12)])

def random_value():
    return "RANDOM_VALUE:%s" % (random_string(),)

class DummySessionFactory(object):
    _data = {}
    _reactor = None
    _expires = {}

    @classmethod
    def retrieve(cls, uid, reactor):
        session_data = cls._data.get(uid, dict())
        return PersistentSessionDict(uid, session_data, cls, reactor)

    @classmethod
    def delete_keys_from_session(cls, uid, keys):
        for key in keys:
            del cls._data[uid][key]
        return cls.df()

    @classmethod
    def df(cls):
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
        cls._expires[uid] = time.time() + timeout
        return cls.df()

    @classmethod
    def get_stored_value(cls, uid, key):
        return cls._data.get(uid, dict()).get(key)


class SessionTests(unittest.TestCase):
    """
    Tests for persistent HTTP connections.
    """
    def setUp(self):
        s = Site(None)
        self.uid = s._mkuid()
        self.dsf = DummySessionFactory()
        self.session = self.dsf.retrieve(self.uid, reactor=reactor)

    def reset(self):
        def check_result_of_clear():
            assert(self.session == {})
        self.session.clear()
        return task.deferLater(reactor, 0, check_result_of_clear)

    def test_setitem(self):
        target_value = random_value()
        self.session["TEST_SETITEM"] = target_value
        assert(target_value != DummySessionFactory.get_stored_value(self.uid, "TEST_SETITEM"))
        def check_result():
            assert(self.session["TEST_SETITEM"] == DummySessionFactory.get_stored_value(self.uid, "TEST_SETITEM") == target_value)
            return self.reset()
        return task.deferLater(reactor, 0, check_result)

    def test_delitem(self):
        target_value = random_value()
        self.session["TEST_DELITEM"] = target_value
        def check_result_of_delitem():
            assert("TEST_DELITEM" not in self.session)
            assert(DummySessionFactory.get_stored_value(self.uid, "TEST_DELITEM") == None)
            return self.reset()
        def check_result_of_setitem():
            assert(self.session["TEST_DELITEM"] == target_value)
            del self.session["TEST_DELITEM"]
            return task.deferLater(reactor, 0, check_result_of_delitem)
        return task.deferLater(reactor, 0, check_result_of_setitem)

    def test_pop(self):
        target_value = random_value()
        self.session["TEST_POP"] = target_value
        def check_result_of_pop():
            assert("TEST_POP" not in self.session)
            assert(DummySessionFactory.get_stored_value(self.uid, "TEST_POP") == None)
            return self.reset()
        def check_result_of_setitem():
            assert(self.session["TEST_POP"] == target_value)
            assert(target_value == self.session.pop("TEST_POP"))
            return task.deferLater(reactor, 0, check_result_of_pop)
        return task.deferLater(reactor, 0, check_result_of_setitem)

    def test_popitem(self):
        target_value = random_value()
        self.session.clear()
        def check_result_of_clear():
            assert(self.session == {})
            self.session["TEST_POPITEM"] = target_value
            return task.deferLater(reactor, 0, check_result_of_setitem)
        def check_result_of_popitem():
            assert(DummySessionFactory.get_stored_value(self.uid, "TEST_POPITEM") == None)
            return self.reset()
        def check_result_of_setitem():
            assert(self.session["TEST_POPITEM"] == target_value)
            assert(("TEST_POPITEM", target_value) == self.session.popitem())
            assert("TEST_POPITEM" not in self.session)
            return task.deferLater(reactor, 0, check_result_of_popitem)
        return task.deferLater(reactor, 0, check_result_of_clear)

    def test_getitem(self):
        target_value = random_value()
        self.session["TEST_GETITEM"] = target_value
        assert(target_value != DummySessionFactory.get_stored_value(self.uid, "TEST_GETITEM"))
        def check_result():
            assert(self.session["TEST_GETITEM"] == DummySessionFactory.get_stored_value(self.uid, "TEST_GETITEM") == target_value)
            return self.reset()
        return task.deferLater(reactor, 0, check_result)

    def test_setdefault(self):
        assert("TEST_SETDEFAULT" not in self.session)
        assert(DummySessionFactory.get_stored_value(self.uid, "TEST_SETDEFAULT") is None)
        target_value = random_value()
        ignored_value = random_value()
        self.session.setdefault("TEST_SETDEFAULT", target_value)

        def check_result_setdefault_ignored():
            assert(self.session["TEST_SETDEFAULT"] == DummySessionFactory.get_stored_value(self.uid, "TEST_SETDEFAULT") == target_value)
            return self.reset()

        def check_result_setdefault():
            assert(self.session["TEST_SETDEFAULT"] == DummySessionFactory.get_stored_value(self.uid, "TEST_SETDEFAULT"))
            self.session.setdefault("TEST_SETDEFAULT", ignored_value)
            assert(self.session["TEST_SETDEFAULT"] == target_value)
            return task.deferLater(reactor, 0, check_result_setdefault_ignored)

        return task.deferLater(reactor, 0, check_result_setdefault)

    def test_update(self):
        assert({} == self.session)
        target_value_a = random_value()
        target_value_b = random_value()
        target_value_c = random_value()
        target_value_d = random_value()
        target_value_a_updated = random_value()

        assert(DummySessionFactory.get_stored_value(self.uid, "TEST_UPDATE_A") is None)
        assert(DummySessionFactory.get_stored_value(self.uid, "TEST_UPDATE_B") is None)
        assert(DummySessionFactory.get_stored_value(self.uid, "TEST_UPDATE_C") is None)
        assert(DummySessionFactory.get_stored_value(self.uid, "TEST_UPDATE_D") is None)

        initial_values = {
                             "TEST_UPDATE_A": target_value_a,
                             "TEST_UPDATE_B": target_value_b,
                             "TEST_UPDATE_C": target_value_c
                         }
        self.session.update(initial_values)

        new_values = {
                         "TEST_UPDATE_A": target_value_a_updated,
                         "TEST_UPDATE_D": target_value_d
                     }

        def check_result_of_update():
            for key, expected_value in initial_values.items():
                assert(self.session[key] == DummySessionFactory.get_stored_value(self.uid, key) == expected_value)

            # Make sure that only the keys we're expecting exist
            assert(self.session.keys() == DummySessionFactory._data[self.uid].keys() == initial_values.keys())

            """
            The first call to .update worked. Now we call .update again to
            modify TEST_UPDATE_A and add TEST_UPDATE_D
            """
            self.session.update(new_values)
            return task.deferLater(reactor, 0, check_result_of_another_update)

        def check_result_of_another_update():
            expected_values = initial_values.copy()
            expected_values.update(new_values)

            for key, expected_value in expected_values.items():
                assert(self.session[key] == DummySessionFactory.get_stored_value(self.uid, key) == expected_value)

            # Make sure that only the keys we're expecting exist
            assert(self.session.keys() == DummySessionFactory._data[self.uid].keys() == expected_values.keys())
            return self.reset()

        return task.deferLater(reactor, 0, check_result_of_update)

    def test_clear(self):
        target_value = random_value()
        self.session["TEST_CLEAR"] = target_value
        def check_result_of_clear():
            assert(self.session == {})
            return self.reset()
        def check_result_of_setitem():
            assert(self.session["TEST_CLEAR"] == target_value)
            self.session.clear()
            return task.deferLater(reactor, 0, check_result_of_clear)
        return task.deferLater(reactor, 0, check_result_of_setitem)

    def test_touch(self):
        target_value = random_value()
        self.session["TEST_TOUCH"] = target_value
        def check_result_of_setitem():
            assert(self.session["TEST_TOUCH"] == target_value)
            assert((time.time() + self.session._session_timeout) - DummySessionFactory._expires[self.uid] < 1)
            return self.reset()
        return task.deferLater(reactor, 0, check_result_of_setitem)

    def test_expire(self):
        target_value = random_value()
        self.session["TEST_EXPIRE"] = target_value
        assert(target_value != DummySessionFactory.get_stored_value(self.uid, "TEST_EXPIRE"))

        def check_result_of_expire():
            assert(not self.session)
            assert(self.uid not in DummySessionFactory._data)
            return self.reset()

        def check_setitem():
            assert(self.session["TEST_EXPIRE"] == DummySessionFactory.get_stored_value(self.uid, "TEST_EXPIRE") == target_value)
            assert(self.uid in DummySessionFactory._data)
            self.session.expire()
            return task.deferLater(reactor, 0, check_result_of_expire)

        return task.deferLater(reactor, 0, check_setitem)
