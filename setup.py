# -*- coding: utf-8 -*-
import os
import re
from distutils.core import setup


def find_packages(path='.'):
    ret = []
    for root, dirs, files in os.walk(path):
        if '__init__.py' in files:
            ret.append(re.sub('^[^A-z0-9_]+', '', root.replace('/', '.')))
    return ret


setup(name='hdf',
      version='0.0.1b',
      description='Hui Distributed Framework,Base On BSCTS Framework',
      author='LiuZhaoHui',
      author_email='niuniu702@qq.com',
      url='https://github.com/mzniuniu/udf',
      license='http://www.apache.org/licenses/LICENSE-2.0.html',
      # packages = find_packages(),
      packages=['hdf'],
      # py_modules=['hdf'],
      )
