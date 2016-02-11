#!/usr/bin/env python

from txredisapi import UnixConnectionPool
from txredisapi import UnixConnection
from txredisapi import ConnectionPool
from twisted.internet import reactor
from twisted.internet import task
from webtest import log

logger = log.get_logger()

def main():
    def eb(f):
        print f.getBriefTraceback()

    def testdelete(ucp=None):
        print("TESTDELETE: %s" % (ucp,))
        df = ucp.delete("d852275ecf54c1bd3697722206038b4")
        return ucp

    def testget(result=None, ucp=None):
        print("TESTGET: %s" % (result,))
        df = ucp.hgetall("d852275ecf54c1bd3697722206038b4")
        df.addCallback(done)
        df.addErrback(eb)

    def done(result=None):
        print("DONE: %s" % (result,))
        reactor.stop()

    def _main():
        ucp = UnixConnectionPool()
        ucp.addCallback(testdelete)
        ucp.addCallback(testset)
        #ucp.addCallback(lambda x:testget(None, x))
        ucp.addErrback(eb)

    def testset(ucp):
        print("TESTSET: %s" % (ucp,))
        df = ucp.hmset("d852275ecf54c1bd3697722206038b4", {"testvalue":"55"})
        df.addCallback(testget, ucp=ucp)
        df.addErrback(eb)
        return df

    reactor.callWhenRunning(_main)
    reactor.run()

if __name__ == '__main__':
    main()

