import os
import sys

extensions = []

master_doc = 'index'
project = 'micawber'
copyright = '2013, charles leifer'

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.dirname(__file__))))
from micawber import __version__
version = release = __version__

exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']
