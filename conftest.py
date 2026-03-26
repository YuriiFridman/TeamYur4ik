"""
Root conftest.py — shared fixtures for the test suite.
"""
import sys
import os

# Ensure both server/ and client/ are on the path for all test modules
_ROOT = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_ROOT, "server"))
sys.path.insert(0, os.path.join(_ROOT, "client"))
