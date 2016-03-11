#!/usr/bin/env python

from zope.interface import Interface, Attribute, implements
from twisted.python.components import registerAdapter
from twisted.web.server import Session
from twisted.application import internet, service
from twisted.python import log
from twisted.web import server
from twisted.web import resource
from twisted.internet import reactor

appname = "webtest"

from webtest.log import get_logger
logger = get_logger(appname)
logger.error("WOAH")

from webtest.web import index
from webtest.site import RedisSite


class ICounter(Interface):
    value = Attribute("An int value which counts up once per page view.")

class Counter(object):
    implements(ICounter)
    def __init__(self, session):
        self.value = 0

registerAdapter(Counter, Session, ICounter)

class CounterResource(resource.Resource):
    isLeaf=True
    def render_GET(self, request):

        logger.error(">>>>>>>>>>>>>>>>>>>>")
        logger.error(request.requestReceived())
	iq = sorted(dir(request.received_headers))
        for item in iq:
            logger.error("    %s" % (item,))

        logger.error(">>>>>>>>>>>>>>>>>>>>")
        session = request.getSession()
        counter = ICounter(session)   
	iq = sorted(dir(counter))
        for item in iq:
            logger.error("    %s" % (item,))
        counter.value += 1
        return "Visit #%d for you!" % (counter.value,)




class Simple(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        df = request.getSession()
        df.addCallback(self.cb, request)
        return df

    def cb(self, session, request):
        someval = session.get("SOMEVAL", 'xxx')
        session['SOMEVAL'] = "HELP"
        return "<html>Hello, world 2!: '%s' %s</html>" % (someval, request.path,)

root = index.Root()
#root.putChild("hoops", Simple())
root.putChild("count", CounterResource())

logger.error("TEST - TAC FILE")

observer = log.PythonLoggingObserver(loggerName=appname)
application = service.Application(appname)
application.setComponent(log.ILogObserver, observer.emit)

site = RedisSite(root)
sc = service.IServiceCollection(application)
i = internet.TCPServer(8081, site)
i.setServiceParent(sc)
