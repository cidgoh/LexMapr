from distutils.core import setup

from setuptools import find_packages

from lexmapr import __version__

classifiers = """
Development Status :: 4 - Beta
Environment :: Console
License :: OSI Approved :: GNU General Public License (GPL)
Intended Audience :: Science/Research
Topic :: Scientific/Engineering
Topic :: Scientific/Engineering :: Bio-Informatics
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3.6
Operating System :: POSIX :: Linux
""".strip().split('\n')

setup(name='lexmapr',
      version=__version__,
      description='A Lexicon and Rule-Based Tool for Translating Short Biomedical Specimen Descriptions into Semantic Web Ontology Terms',
      author='Gurinder Gosal',
      author_email='gosal.gps@gmail.com',
      url='https://github.com/lexmapr/LexMapr',
      license='GPL-3.0',
      classifiers=classifiers,
      install_requires=[
          'nltk==3.4.5',
          'wikipedia==1.4.0',
          'inflection==0.3.1',
          'python-dateutil==2.7.3',
          'rdflib==4.2.2',
      ],
      python_requires='>=3.5, <3.8',
      test_suite='nose.collector',
      tests_require=['nose'],
      packages=find_packages(),
      include_package_data=True,
      scripts=['bin/lexmapr']
)
