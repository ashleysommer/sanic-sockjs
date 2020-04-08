import codecs
import os
import re
from setuptools import setup, find_packages

with codecs.open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "sanic_sockjs", "__init__.py"),
    "r",
    "latin1",
) as fp:
    try:
        version = re.findall(r'^__version__ = "([^"]+)"\r?$', fp.read(), re.M)[0]
    except IndexError:
        raise RuntimeError("Unable to determine version.")

with codecs.open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "requirements.txt"),
    "r",
    "latin1",
) as fp:
    all_lines = fp.read()
    install_requires = [a.strip(' \r\n\t') for a in all_lines.split('\n') if len(a)]


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()


setup(
    name="sanic-sockjs",
    version=version,
    description=("SockJS server implementation for Sanic."),
    long_description="\n\n".join((read("README.rst"), read("CHANGES.txt"))),
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Internet :: WWW/HTTP",
        "Framework :: AsyncIO",
    ],
    author="Ashley Sommer",
    author_email="ashleysommer@gmail.com",
    url="https://github.com/ashleysommer/sanic-sockjs/",
    license="Apache 2",
    packages=find_packages(),
    python_requires=">=3.6.0",
    install_requires=install_requires,
    include_package_data=True,
    zip_safe=False,
)
