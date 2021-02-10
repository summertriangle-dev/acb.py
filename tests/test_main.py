import os
from acb_py import acb, disarm

def test_speedup_compilation():
    assert(disarm._acb_speedup)
