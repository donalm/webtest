#!/usr/bin/env python

from txredisapi import UnixConnectionPool
from twisted.internet import reactor as txreactor
from twisted.internet import task
from webtest import log

logger = log.get_logger()


"""
Store some data in the cookie - encrypted with a salt
"""

def logging_errback(f, label="logging_errback"):
    logger.error("%s: %s" % (label, f.getBriefTraceback()))


class PersistentSessionDict(dict):
    """
    A user's session with a system. Note that we're subclassing dict. And may
    the lord have mercy on our souls.

    @ivar uid: A unique identifier for the session, C{bytes}.
    @ivar dictionary: The default session data. Must be a dict. Probably empty.
    @ivar factory: The session factory that creates instances of this class and
        mediates interactions with the persistence mechanism (probably Redis)
    @ivar _reactor: An object providing L{IReactorTime} to use for scheduling
        expiration.
    """

    # Default lifetime for session data in seconds
    sessionTimeout = 900

    def __init__(self, uid, dictionary, factory, _reactor=False, _sessionTimeout=None):
        dict.__init__(self, dictionary)
        self._modified = set()
        self._removed = set()
        self.uid = uid
        self._df = None
        self._factory = factory
        self._reactor = _reactor or txreactor
        self._sessionTimeout = _sessionTimeout or PersistentSessionDict.sessionTimeout

    def __setitem__(self, key, value):
        """
        Override the __setitem__ method in dict to ensure that we capture any
        keys that have been modified before we call the method on the parent
        class
        @ivar key: The identifying key
        @ivar value: The value
        """
        if not self.get(key) == value:
            self._modified.add(key)
            self._force_flush()
        return dict.__setitem__(self, key, value)

    def _force_flush(self):
        """
        Create a task.deferLater that will save the data in this object using
        the factory's persistence mechanism (probaby Redis) as soon as we release
        control of the event loop.
        """
        if self._df is None:
            self._df = task.deferLater(self._reactor, 0, self._flush)
        return self._df

    def startCheckingExpiration(self):
        """
        Start expiration tracking. We rely on the factory to do this for us, which
        might be problematic for non-Redis persistence mechanisms, as they may not
        be capable of expiring data for us automatically.

        @return: C{None}
        """
        self.touch()

    def setdefault(self, key, default):
        """
        Override the setdefault method in dict to ensure that we capture any
        keys that have been modified before we call setdefault on the parent
        class
        @ivar key: The identifying key
        @ivar deault: The default value
        """
        if not key in self:
            self._modified.add(key)
            self._force_flush()
        return dict.setdefault(self, key, default)

    def pop(self, *args):
        """
        Override the pop method in dict to ensure that we capture any key that
        has been removed before we call pop on the parent class
        @ivar key: The identifying key
        @ivar deault: The default value
        """
        try:
            self._modified.remove(args[0])
            self._removed.add(args[0])
            self._force_flush()
        except Exception, e:
            pass
        return dict.pop(self, *args)

    def popitem(self):
        """
        Override the popitem method in dict to ensure that we capture any key that
        has been removed after we call popitem on the parent class
        """
        rval = dict.popitem(self)
        try:
            self._modified.remove(rval[0])
            self._removed.add(rval[0])
            self._force_flush()
        except Exception, e:
            logger.error("ERROR: Unexpected error on popitem for key/value %s:%s %s" % (rval[0], rval[1], e,))
        return rval

    def notifyOnExpire(self, callback):
        """
        In generic Twisted Web, we would call this callback when the session
        expires or logs out. There's no simple way to make this work when we
        run in a multi-daemon-process architecture.
        """
        raise NotImplementedError("ERROR: notifyOnExpire cannot work across multiple processes.")

    def clear(self):
        """
        Override the clear method in dict to ensure that we capture any key that
        has been removed before we call clear on the parent class
        """
        [self._removed.add(key) for key in self.keys()]
        self._modified = set()
        dict.clear(self)

    def expire(self):
        """
        The expire method deletes the data from this object and notifies the factory to
        delete the data from the persistence mechanism.
        """
        # This is the one case in which we want to delete data from this class without
        # storing keys in self._modified or self._removed
        dict.clear(self)
        self._factory.expire(self.uid)

    def update(self, *args, **kwargs):
        """
        Override the update method in dict to ensure that we capture any key that
        has been updated before we call update on the parent class
        """
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
        """
        The _flush method is called by a 'deferLater(0, ' assignment and
        attempts to identify all the modified or deleted keys on the data dict,
        so that the changes can be handed to the factory class to be saved by
        the persistence mechanism (e.g. Redis).
        """

        """
        Restore the deferred to None so that another 'save' sweep can be
        scheduled
        """
        self._df = None

        if not self._removed and not self._modified:
            return

        """
        Copy the set of keys that have been removed to a tuple, and reset the
        _removed attribute to the empty set, ready for fresh modifications
        """
        removed_keys = tuple(self._removed)
        self._removed = set()

        if removed_keys:
            """
            if 'removed_keys' is not empty, ask the factory class to delete
            those keys from the session
            """
            df = self._factory.delete_keys_from_session(self.uid, removed_keys)
            df.addErrback(logging_errback, "self._factory.delete_keys_from_session")

        """
        Copy the set of keys that have been modified to a tuple, and reset the
        _modified attribute to the empty set, ready for fresh modifications
        """
        modified_keys = tuple(self._modified)
        self._modified = set()

        patch = {}
        if modified_keys:
            for key in modified_keys:
                patch[key] = self[key]

            df = self._factory.patch_session(self.uid, patch)
            df.addErrback(logging_errback, "self._factory.patch_session")

        """
        Update the expiry time on the data for our UID
        """
        self.touch()

    def touch(self):
        """
        Update the expiry time on the data for our UID
        """
        df = self._factory.touch_session(self.uid, self.sessionTimeout)
        df.addErrback(logging_errback, "self._factory.touch_session")


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
    def _connected(cls, ucp):
        """
        We successfully connected to a Redis service. Persist the resulting
        connection object as an attribute on the class
        """
        cls._pool = ucp
        return ucp

    @classmethod
    def _connection_failed(cls, f):
        """
        Log an escalate connection failures
        """
        logger.error("ERROR: connection to Redis failed: %s", f.getBriefTraceback())
        return f

    @classmethod
    def connect(cls):
        """
        Establish a connection to the Redis service (if none exists)
        """
        if cls._pool is None:
            df = UnixConnectionPool()
            df.addCallback(cls._connected)
            df.addErrback(cls._connection_failed)
            return df
        return cls._pool

    @classmethod
    def connect_and_execute(cls, method, *args, **kwargs):
        """
        This method should be used as a wrapper around methods that require a
        connection to Redis. If no connection exists, one is created before the
        'wrapped' method is executed.
        """
        try:
            df = method(cls._pool, *args, **kwargs)
        except AttributeError:
            df = cls.connect()
            df.addCallback(method, *args, **kwargs)
            df.addErrback(logging_errback, "connect_and_execute")

        return df

    @classmethod
    def retrieve(cls, uid, reactor):
        """
        Connect to Redis and get data from the persistence layer for a UID
        """
        return cls.connect_and_execute(cls._retrieve, uid, reactor)

    @classmethod
    def _retrieve(cls, pool, uid, reactor):
        """
        Get data from the persistence layer for a UID
        """
        session_data_df = pool.hgetall(uid)
        session_data_df.addCallback(cls._retrieve_callback, uid, reactor)
        session_data_df.addErrback(logging_errback, "pool.hgetall")
        return session_data_df

    @classmethod
    def _retrieve_callback(cls, session_data, uid, reactor):
        """
        Inject the dict we retrieved from the storage layer into a
        PersistentSessionDict obect and return it
        """
        return PersistentSessionDict(uid, session_data, cls, reactor)

    @classmethod
    def expire(cls, uid):
        """
        Connect to Redis and expire/logout a session.
        """
        return cls.connect_and_execute(cls._expire, uid)

    @classmethod
    def _expire(cls, pool, uid):
        """
        Expire/logout a session.
        """
        return pool.delete(uid)

    @classmethod
    def delete_keys_from_session(cls, uid, keys):
        """
        Connect to Redis and remove keys from the session hash
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
        Connect to Reis and set or update values in the session hash
        """
        return cls.connect_and_execute(cls._patch_session, uid, patch)

    @classmethod
    def _patch_session(cls, pool, uid, patch):
        """
        Set or update values in the session hash
        """
        return pool.hmset(uid, patch)

    @classmethod
    def touch_session(cls, uid, timeout):
        """
        Connect to Redis and update the session expiry
        """
        return cls.connect_and_execute(cls._touch_session, uid, timeout)

    @classmethod
    def _touch_session(cls, pool, uid, timeout):
        """
        Update the session expiry
        """
        return pool.expire(uid, timeout)


def main():
    pass

if __name__ == '__main__':
    main()
