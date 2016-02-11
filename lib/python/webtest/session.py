#!/usr/bin/env python

from txredisapi import UnixConnectionPool
from txredisapi import UnixConnection
from txredisapi import ConnectionPool
from twisted.internet import reactor
from twisted.internet import task
from webtest import log

logger = log.get_logger()


"""
Store some data in the cookie - encrypted with a salt
"""

def logger_error(str, *args):
    print(str % args)

def eb(f, label="EB"):
    logger.error("%s: %s" % (label, f.getBriefTraceback()))


class PersistentSessionDict(dict):
    sessionTimeout = 900
    def __init__(self, uid, dictionary, factory, r=False):
        dict.__init__(self, dictionary)
        self._modified = set()
        self._removed = set()
        self.uid = uid
        self._df = None
        self._factory = factory
        self._reactor = r or reactor
        logger.error("KEYS: %s", self.keys())
        logger.error("SRC:  %s", dictionary.keys())

    def __setitem__(self, key, value):
        if not self.get(key) == value:
            self._modified.add(key)
            self._force_flush()
        return dict.__setitem__(self, key, value)

    def _force_flush(self):
        if self._df is None:
            self._df = task.deferLater(self._reactor, 0, self._flush)
        return self._df

    def startCheckingExpiration(self):
        """
        Start expiration tracking.

        @return: C{None}
        """
        self.touch()

    def setdefault(self, key, default):
        if not key in self:
            self._modified.add(key)
            self._force_flush()
        return dict.setdefault(self, key, default)

    def pop(self, *args):
        try:
            self._modified.remove(args[0])
            self._removed.add(args[0])
            self._force_flush()
        except Exception, e:
            pass
        return dict.pop(self, *args)

    def popitem(self):
        rval = dict.popitem(self)
        try:
            self._modified.remove(rval[0])
            self._removed.add(rval[0])
            self._force_flush()
        except Exception, e:
            logger_error("ERROR: Unexpected error on popitem for key/value %s:%s %s" % (rval[0], rval[1], e,))
        return rval

    def notifyOnExpire(self, callback):
        """
        Call this callback when the session expires or logs out.
        """
        raise NotImplementedError("ERROR: notifyOnExpire cannot work across multiple processes.")

    def clear(self):
        [self._removed.add(key) for key in self.keys()]
        self._modified = set()
        dict.clear(self)

    def expire(self):
        self._factory.expire(self.uid)

    def update(self, *args, **kwargs):
        try:
            new_dict = args[0]
            for key in new_dict.items():
                self._modified.add(key)
                try:
                    self._removed.remove(key)
                except Exception:
                    pass
        except Exception:
            pass
        for key in kwargs.keys():
            self._modified.add(key)
        return dict.update(self, *args, **kwargs)

    def _flush(self):
        logger.error("_FLUSH: %s", self._modified)
        if not self._removed and not self._modified:
            logger.error("RETURNING - NO CHANGES")
            return

        logger.error("_FLUSH 2")
        self._df = None

        removed_keys = tuple(self._removed)
        self._removed = set()
        logger.error("_FLUSH removed_keys: %s", removed_keys)
        if removed_keys:
            logger.error("_FLUSH 3")
            df = self._factory.delete_keys_from_session(self.uid, removed_keys)
            df.addCallback(lambda x:logger.error("Deleted keys: %s", x))
            df.addErrback(eb, "delete keys from session")
            logger.error("_FLUSH 3b")

        logger.error("_FLUSH 2a")
        modified_keys = self._modified
        logger.error("_FLUSH 2b")
        self._modified = set()
        logger.error("_FLUSH 2c: %s", modified_keys)
        patch = {}
        logger.error("_FLUSH 2d")
        for key in modified_keys:
            patch[key] = self[key]
        logger.error("PATCH SESSION: %s", patch)
        df = self._factory.patch_session(self.uid, patch)
        df.addCallback(lambda x:logger.error("Patched: %s", x))
        df.addErrback(eb, "patch session")
        self.touch()

    def touch(self):
        logger.error("TOUCH SESSION")
        df = self._factory.touch_session(self.uid, self.sessionTimeout)
        df.addCallback(lambda x:logger.error("Touched: %s", x))
        df.addErrback(eb, "touch session")


class RedisSessionFactory(dict):
    """
    A user's session with a system.

    This utility class contains no functionality, but is used to
    represent a session.

    @ivar uid: A unique identifier for the session, C{bytes}.
    @ivar _reactor: An object providing L{IReactorTime} to use for scheduling
        expiration.
    @ivar sessionTimeout: timeout of a session, in seconds.
    """
    sessionTimeout = 900

    _expireCall = None
    _pool = None

    @classmethod
    def _ready(cls, ucp):
        cls._pool = ucp
        return ucp

    @classmethod
    def _unready(cls, f):
        logger.error("unready")
        logger_error("ERROR: %s", f.getBriefTraceback())
        return f

    @classmethod
    def connect(cls):
        if cls._pool is None:
            df = UnixConnectionPool()
            df.addCallback(cls._ready)
            df.addErrback(cls._unready)
            return df
        return cls._pool

    @classmethod
    def retrieve(cls, uid, reactor):
        logger.error("retrieve")
        return cls.connect_and_execute(cls._retrieve, uid, reactor)

    @classmethod
    def _retrieve(cls, pool, uid, reactor):
        logger.error("_retrieve: %s  %s" % (uid, type(uid),))
        session_data_df = pool.hgetall(uid)
        def qi(session_data):
            logger.error("QI %s" % (session_data,))
            return PersistentSessionDict(uid, session_data, cls, reactor)
        session_data_df.addCallback(qi)
        #return PersistentSessionDict(uid, session_data, cls, reactor)
        session_data_df.addErrback(cls._unready)
        return session_data_df


    @classmethod
    def expire(cls, uid):
        """
        Expire/logout a session.
        """
        return cls.connect_and_execute(cls._expire, uid)


    @classmethod
    def _expire(cls, pool, uid):
        """
        Expire/logout a session.
        """
        return pool.delete(uid)


    @classmethod
    def connect_and_execute(cls, method, *args, **kwargs):
        logger.error("Connect & Execute: %s" % (method,))
        try:
            df = method(cls._pool, *args, **kwargs)
        except AttributeError:
            df = cls.connect()
            df.addCallback(method, *args, **kwargs)
            df.addErrback(eb, "AttributeError")

        return df


    @classmethod
    def delete_keys_from_session(cls, uid, keys):
        """
        Remove keys from the session hash
        """
        return cls.connect_and_execute(cls._delete_keys_from_session, uid, keys)


    @classmethod
    def _delete_keys_from_session(cls, pool, uid, keys):
        """
        Remove keys from the session hash
        """
        return pool.hdel(self.uid, *keys)


    @classmethod
    def patch_session(cls, uid, patch):
        """
        Set or update values in the session hash
        """
        logger.error("patch session")
        return cls.connect_and_execute(cls._patch_session, uid, patch)


    @classmethod
    def _patch_session(cls, pool, uid, patch):
        """
        Set or update values in the session hash
        """
        logger.error("_patch session: %s", patch)
        return pool.hmset(uid, patch)


    @classmethod
    def touch_session(cls, uid, timeout):
        """
        Update the session expiry
        """
        return cls.connect_and_execute(cls._touch_session, uid, timeout)

    @classmethod
    def _touch_session(cls, pool, uid, timeout):
        """
        Update the session expiry
        """
        return pool.expire(uid, timeout)


def main():
    def eb(f):
        print f.getBriefTraceback()

    def testget(result=None, ucp=None):
        print("TESTGET: %s" % (result,))
        df = ucp.get("testkey")
        df.addCallback(done)

    def done(result=None):
        print("DONE: %s" % (result,))
        reactor.stop()

    def _main():
        ucp = UnixConnectionPool()
        ucp.addCallback(testset)
        ucp.addErrback(eb)

    def testset(ucp):
        print("TESTSET: %s" % (ucp,))
        df = ucp.set("testkey", "testvalue")
        df.addCallback(testget, ucp=ucp)
        df.addErrback(eb)
        return df

    reactor.callWhenRunning(_main)
    reactor.callWhenRunning(TxRedis.init)
    reactor.run()

def ko(x):
    print("KO:%s" % (x,))



if __name__ == '__main__':
    main()
