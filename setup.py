from setuptools import setup, find_packages
import sys, os

# run :python setup.py sdist upload

version = '0.1.4'

setup(name='pymysqlrpc',
      version=version,
      description="a rpc framework implement mysql server protocol on top of gevent",
      long_description="""\
pymysqlrpc is a very interesting, very simple RPC framework, implement mysql server protocol,  on top of gevent,  map one call of mysql stored procedures to python's a function or a method of an instance.""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='gevent mysql rpc',
      author='roger.luo',
      author_email='feihu.roger@gmail.com',
      url='http://github.com/feihuroger/pymysqlrpc',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'example', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
