#!/usr/bin/env python
import os
import unittest


def collect():
    start_dir = os.path.abspath(os.path.dirname(__file__))
    return unittest.defaultTestLoader.discover(start_dir)


if __name__ == '__main__':
    unittest.main(module='tests')

