#!/usr/bin/env python

import os
import socket
from zope.interface import Interface, Attribute, implements
from twisted.web.server import Session
from twisted.application import internet, service
from twisted.python import log
from twisted.web import server
from twisted.web import resource
from twisted.internet import reactor
from twisted.internet import endpoints

instance_id = int(os.environ.get("WEBTEST_INSTANCE", 0))

appname = "webtest"

from webtest.log import get_logger
logger = get_logger(appname, instance_id)
logger.error("OBTAINED LOG")

from webtest.web import index
from webtest.site import RedisSite




def get_endpoint(port):
    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    skt.bind(('0.0.0.0', port))

    # backlog == 50
    skt.listen(50)

    # Pass the socket into an endpoint
    return endpoints.AdoptedStreamServerEndpoint(reactor, skt.fileno(), skt.family)



root = index.Root()

logger.error("TEST - TAC FILE")

observer = log.PythonLoggingObserver(loggerName=appname)
application = service.Application(appname)
application.setComponent(log.ILogObserver, observer.emit)

site = RedisSite(root)
sc = service.IServiceCollection(application)
webservice = internet.StreamServerEndpointService(get_endpoint(8080), site)
webservice.setServiceParent(sc)
