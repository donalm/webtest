#!/usr/bin/env python

from txredisapi import UnixConnectionPool
from txredisapi import UnixConnection
from txredisapi import ConnectionPool
from twisted.internet import reactor

from cryptography import fernet
'''
x=fernet.Fernet.generate_key()
print(x)
x=fernet.Fernet.generate_key()
print(x)
print(type(x))
print(fernet.Fernet(x))


def main():
    fernet000 = fernet.Fernet(fernet.Fernet.generate_key())
        fernet001 = fernet.Fernet(fernet.Fernet.generate_key())

            # New keys go to the front of the keykchain
                fernet_keychain = fernet.MultiFernet([fernet001, fernet000])

                    f = fernet000
                        token = f.encrypt(b"Secret Message")
                            plaintext = fernet_keychain.decrypt(token)
                                print plaintext
'''


"""
Store some data in the cookie - encrypted with a salt
"""

class WebSession(object):
    def __init__(self, request):
        pass


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
        ucp = UnixConnection()
        ucp.addCallback(testset)
        ucp.addErrback(eb)

    def testset(ucp):
        print("TESTSET: %s" % (ucp,))
        df = ucp.set("testkey", "testvalue")
        df.addCallback(testget, ucp=ucp)
        df.addErrback(eb)
        return df

    print 'main'
    reactor.callWhenRunning(_main)
    reactor.run()


if __name__ == '__main__':
    main()
