#!/usr/bin/env python

from twisted.web import resource

class Root(resource.Resource):

    def render_GET(self, request):
        session = request.getSession()
        return '''<html><body><ul>
                    <li><a href="/json">json</a></li>
                    <li><a href="/db">db</a></li>
                    <li><a href="/queries">queries</a></li>
                    <li><a href="/updates">updates</a></li>
                    <li><a href="/fortunes">fortunes</a></li>
                    <li><a href="/plaintext">plaintext</a></li>
                  </ul></body></html>'''

    def getChild(self, name, request):
        return self
