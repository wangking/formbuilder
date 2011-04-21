# coding:utf-8
import distutils.core
import sys
# Importing setuptools adds some features like "setup.py develop", but
# it's optional so swallow the error if it's not there.
try:
    import setuptools
except ImportError:
    pass

# Build the epoll extension for Linux systems with Python < 2.6
extensions = []
major, minor = sys.version_info[:2]
python_26 = (major > 2 or (major == 2 and minor >= 6))

distutils.core.setup(
    name="formbuilder",
    version="1.1",
    packages = ["formbuilder"],
    ext_modules = extensions,
    author="wang huaiyu",
    author_email="wang.huaiyu.shui@gmail.com",
    url="http://www.aoyoute.com/",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    description="formbuilder is built based on web2py sqlform",
)

