import os
from setuptools import setup, find_packages

f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
readme = f.read()
f.close()

setup(
    name='micawber',
    version="0.2.5",
    description='a small library for extracting rich content from urls',
    long_description=readme,
    author='Charles Leifer',
    author_email='coleifer@gmail.com',
    url='http://github.com/coleifer/micawber/',
    packages=find_packages(),
    package_data = {
        'micawber': [
            'contrib/mcdjango/templates/micawber/*.html',
        ],
        'examples': [
            #'requirements.txt',
            '*/static/*.css',
            '*/templates/*.html',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    test_suite='runtests.runtests',
)
