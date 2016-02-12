#!/usr/bin/env python

from txredisapi import UnixConnectionPool
from webtest.session import PersistentSessionDict
from webtest import log

logger = log.get_logger()

def logging_errback(f, label="logging_errback"):
    logger.error("%s: %s" % (label, f.getBriefTraceback()))


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
