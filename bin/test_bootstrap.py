#!/usr/bin/pypy
import os

print("\n")

PYTHONPATH = os.environ.get("PYTHONPATH")
APPNAME = os.environ.get("APPNAME")

PROJECT_DIRECTORY_ENV = "%s_PROJECT_DIRECTORY" % (APPNAME.upper(),)
PROJECT_DIRECTORY = os.environ.get(PROJECT_DIRECTORY_ENV)

print("PYTHONPATH: %s" % (PYTHONPATH,))
print("APPNAME: %s" % (APPNAME,))
print("PROJECT_DIRECTORY_ENV: %s" % (PROJECT_DIRECTORY_ENV,))
print("PROJECT_DIRECTORY: %s" % (PROJECT_DIRECTORY,))

assert(PYTHONPATH == "/home/donal/Geek/%s/lib/python" % (APPNAME,))
assert(APPNAME == "%s" % (APPNAME,))
assert(PROJECT_DIRECTORY == "/home/donal/Geek/%s" % (APPNAME,))

print("OK!\n\n")
