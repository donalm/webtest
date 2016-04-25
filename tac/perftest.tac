#!/usr/bin/env python

import cgi
import json
import random
from operator import itemgetter
from zope.interface import Interface, Attribute, implements
from twisted.python.components import registerAdapter
from twisted.web.server import Session
from twisted.application import internet, service
from twisted.python import log
from twisted.web import server
from twisted.web import resource
from twisted.internet import reactor
from twisted.internet import defer

from twisted.web import template #import Element, renderer, XMLFile

class FortunesElement(template.Element):
    loader = template.XMLString("""
<table xmlns:t="http://twistedmatrix.com/ns/twisted.web.template/0.1">
    <tr t:render="fortunes"><td><t:slot name="id"/></td>
    <td><t:slot name="message"/></td></tr>
</table>
    """.strip())

    def __init__(self, data):
        self.data = data
        return template.Element.__init__(self)

    @template.renderer
    def fortunes(self, request, tag):
        for fortune in self.data:
            yield tag.clone().fillSlots(id=str(fortune["id"]), message=fortune['message'])

appname = "perftest"

from webtest.log import get_logger
logger = get_logger(appname)
logger.error("WOAH")

from webtest.web import index
from webtest.db_pool import Pool

def initialize(appname):
    pool = Pool(appname)
    df = pool.start()
    df.addCallback(lambda x: logger.error(x))
    df.addErrback(lambda f: logger.error(f.getBriefTraceback()))

reactor.callWhenRunning(initialize, appname)

class JsonPage(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        msg = {"message":"Hello, World!"}
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        return json.dumps(msg)


class BaseQuery(resource.Resource):
    isLeaf = True
    db_pool = Pool(appname)
    srandom = random.SystemRandom()

    @classmethod
    def randint(cls):
        return cls.srandom.randint(1,10000)

    @classmethod
    def eb2(cls, f):
        logger.error(f.getBriefTraceback())

    @classmethod
    def eb(cls, f, request):
        msg = f.getBriefTraceback()
        logger.error(msg)
        request.write(json.dumps({"ERROR":msg}))
        request.finish()

class Fortunes(BaseQuery):
    def render_GET(self, request):
        df = BaseQuery.db_pool.runQuery("SELECT id, message FROM Fortune")
        df.addCallback(Fortunes.cb, request)
        df.addErrback(Fortunes.eb, request)
        request.responseHeaders.addRawHeader(b"content-type", b"text/html; charset=utf-8")
        request.write('<!DOCTYPE html>\n')
        return server.NOT_DONE_YET

    @classmethod
    def cb(cls, data, request):
        data.append({"id":-1, "message":"Additional fortune added at request time."})
        esc = cgi.escape
        data = sorted(data, key=itemgetter("message"))
        e = FortunesElement(data)
        df = template.flatten(request, e, request.write)
        df.addCallback(Fortunes.done, request)
        df.addErrback(BaseQuery.eb, request)

    @classmethod
    def done(cls, r, request):
        request.finish()

class Db(BaseQuery):
    def render_GET(self, request):
        id = BaseQuery.randint()
        df = BaseQuery.db_pool.runQuery("SELECT id, randomNumber FROM World WHERE id=%d" % (id,))
        df.addCallback(self.cb, request)
        df.addErrback(BaseQuery.eb, request)
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        return server.NOT_DONE_YET

    def cb(self, data, request):
        rval = data[0]
        request.write(json.dumps(rval))
        request.finish()

class PlainText(BaseQuery):
    def render_GET(self, request):
        request.responseHeaders.addRawHeader(b"content-type", b"text/plain")
        return "Hello, World!"

    def cb(self, data, request):
        rval = data[0]
        request.write(json.dumps(rval))
        request.finish()

class Updates(BaseQuery):
    def render_GET(self, request):
        try:
            queries = max(1, min(500, int(request.args.get("queries",[1])[0])))
        except Exception, e:
            queries = 1

        df_list = []
        for id in [BaseQuery.randint() for x in range(queries)]:
            df = BaseQuery.db_pool.runQuery("SELECT id, randomNumber FROM World WHERE id=%d" % (id,))
            df.addCallback(lambda x: x.pop())
            df_list.append(df)

        df_list = defer.DeferredList(df_list)
        df_list.addCallback(Updates.cb, request)
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        return server.NOT_DONE_YET

    @classmethod
    def cb(cls, data, request):
        rval = []
        insert = []
        for item in data:
            rval.append({"id":item[1]['id'], "randomNumber":BaseQuery.randint()})
            insert.append("(%d, %d)" % (rval[-1]['id'], rval[-1]['randomNumber'],))

        query = '''update World as W set randomNumber = fresh.randomNumber from (values %s ) as fresh(randomNumber, id) where fresh.randomNumber = W.randomNumber;''' % (", ".join(insert),)
        df = BaseQuery.db_pool.runOperation(query)
        df.addErrback(BaseQuery.eb2)
        request.write(json.dumps(rval))
        request.finish()


class Queries(BaseQuery):
    def render_GET(self, request):
        try:
            queries = max(1, min(500, int(request.args.get("queries",[1])[0])))
        except Exception, e:
            queries = 1

        df_list = []
        for id in [BaseQuery.randint() for x in range(queries)]:
            df = BaseQuery.db_pool.runQuery("SELECT id, randomNumber FROM World WHERE id=%d" % (id,))
            df.addCallback(lambda x: x.pop())
            df_list.append(df)

        df_list = defer.DeferredList(df_list)
        df_list.addCallback(Queries.cb, request)
        return server.NOT_DONE_YET

    @classmethod
    def cb(cls, data, request):
        rval = [item[1] for item in data]
        request.write(json.dumps(rval))
        request.finish()

reactor.callLater(30, reactor.stop)

root = index.Root()
root.putChild("json", JsonPage())
root.putChild("db", Db())
root.putChild("queries", Queries())
root.putChild("updates", Updates())
root.putChild("fortunes", Fortunes())
root.putChild("plaintext", PlainText())

logger.error("TEST - TAC FILE")

observer = log.PythonLoggingObserver(loggerName=appname)
application = service.Application(appname)
application.setComponent(log.ILogObserver, observer.emit)

site = server.Site(root)
sc = service.IServiceCollection(application)
i = internet.TCPServer(8081, site)
i.setServiceParent(sc)
