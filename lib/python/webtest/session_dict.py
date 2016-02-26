#!/usr/bin/env python

from twisted.internet import reactor as txreactor
from twisted.internet import task
from webtest import log

logger = log.get_logger()

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

    def __init__(self, uid, dictionary, factory, _reactor=False, session_timeout=None):
        dict.__init__(self, dictionary)
        self._modified = set()
        self._removed = set()
        self.uid = uid
        self._df = None
        self._factory = factory
        self._reactor = _reactor or txreactor
        self._session_timeout = session_timeout or PersistentSessionDict.sessionTimeout

    def __setitem__(self, key, value):
        """
        Override the __setitem__ method in dict to ensure that we capture any
        keys that have been modified before we call the method on the parent
        class
        @ivar key: The identifying key
        @ivar value: The value
        """
        self._removed.discard(key)
        if not self.get(key) == value:
            self._modified.add(key)
            self._force_flush()
        return dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        """
        Override the __delitem__ method in dict to ensure that we capture any
        keys that have been deleted before we call the method on the parent
        class
        @ivar key: The identifying key
        @ivar value: The value
        """
        if key in self:
            self._removed.add(key)
            self._modified.discard(key)
            self._force_flush()
        return dict.__delitem__(self, key)

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
        self._removed.discard(key)
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
            self._modified.discard(args[0])
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
            self._modified.discard(rval[0])
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
        self._force_flush()
        return dict.clear(self)

    def expire(self):
        """
        The expire method deletes the data from this object and notifies the factory to
        delete the data from the persistence mechanism.
        """
        # This is the one case in which we want to delete data from this class without
        # storing keys in self._modified or self._removed, and without flushing the
        # data to the storage layer, since we're about to 'expire' our data from the
        # storage layer completely
        dict.clear(self)
        self._factory.expire(self.uid)

    def update(self, *args, **kwargs):
        """
        Override the update method in dict to ensure that we capture any key that
        has been updated before we call update on the parent class
        """
        try:
            new_dict = args[0]
            for key in new_dict.keys():
                self._modified.add(key)
                self._removed.discard(key)
        except Exception:
            pass
        for key in kwargs.keys():
            self._modified.add(key)
            self._removed.discard(key)
        self._force_flush()
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
        df = self._factory.touch_session(self.uid, self._session_timeout)
        df.addErrback(logging_errback, "self._factory.touch_session")


