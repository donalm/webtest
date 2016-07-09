#!/usr/bin/env python

from twisted.internet import reactor
from twisted.internet import endpoints
from twisted.application import internet
from twisted.application import service
from twisted.web import server
from twisted.web import static

CERTSDIR = "/var/www/certs"
FILESDIR = "/var/www/html"

endpoint = endpoints.serverFromString(reactor, 'lets:%s:tcp:443' % (CERTSDIR,))

serverFactory = server.Site(static.File(FILESDIR))

application = service.Application('Twisted Web + ACME + HTTP/2 Example')

s = internet.StreamServerEndpointService(endpoint, serverFactory)
s.setServiceParent(application)
