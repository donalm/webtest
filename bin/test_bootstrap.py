#!/usr/bin/pypy
import os

print("\n")

PYTHONPATH = os.environ.get("PYTHONPATH")
APPNAME = os.environ.get("APPNAME")
WEBTEST_PROJECT_DIRECTORY = os.environ.get("WEBTEST_PROJECT_DIRECTORY")

print("PYTHONPATH: %s" % (PYTHONPATH,))
print("APPNAME: %s" % (APPNAME,))
print("WEBTEST_PROJECT_DIRECTORY: %s" % (WEBTEST_PROJECT_DIRECTORY,))

assert(PYTHONPATH == "/home/donal/Geek/webtest/lib/python:/home/donal/Geek/txl/lib/python")
assert(APPNAME == "webtest")
assert(WEBTEST_PROJECT_DIRECTORY == "/home/donal/Geek/webtest")

print("OK!\n\n")
