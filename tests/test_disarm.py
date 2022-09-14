import binascii
import hashlib
from acb import disarm
disarm._acb_speedup = None

import _acb_speedup

TVEC1 = """
FFFF346A5B597EDB1EE48806593CAB68
6B7A8E1EBE668CFCE4FC0770E7F4A31E
48236E86B2EEFB95B261582798A66A5C
000000715C6C00000000000000000000
80067F005028689CC200C200808880EF
7160275D81E1BE94DD9D8F6C33880070
1F7D7D571F28529A22525AF66E6CBEC2
A559ED3BF35CF0E013E64234D7D1A2A5
B5FBAC4390663B640CA681DE2D6AB3C2
312194E30F50B25A6B356AC2BBBEC985
EC927CEA45A1C918CD0BB19AE1223942
77F876191AC8C6E3EE304A1ABF438F54
FF2D141AFB28B1E73CC2
""".replace("\n", "").replace(" ", "")

TVEC2 = """
C8C3C10002000060E6EDF4000100BB80
000000CC008001B5E3EFEDF000CC010F
0101804D00070000E3E9F0E80038F0E1
E4000000000000000000000000000000
00000000000000000000000000000000
0000000000000000000000000000
""".replace("\n", "").replace(" ", "")

def test_checksum():
    vec1 = binascii.unhexlify(TVEC1)
    assert _acb_speedup.checksum_fast(vec1) == 0x36cb
    assert disarm.checksum(vec1) == 0x36cb
    
    vec2 = binascii.unhexlify(TVEC2)
    assert _acb_speedup.checksum_fast(vec2) == 0xa8cb
    assert disarm.checksum(vec2) == 0xa8cb

    block1 = bytearray(len(vec1) + 2)
    block1[:len(vec1)] = vec1
    _acb_speedup.checksum_block_fast(block1)
    assert block1[-2:] == b"\x36\xcb"

    block2 = bytearray(len(vec2) + 2)
    block2[:len(vec2)] = vec2
    _acb_speedup.checksum_block_fast(block2)
    assert block2[-2:] == b"\xa8\xcb"

TVEC3 = """
C8C3C10002000060E6EDF4000100BB80
00000000008001B5E3EFEDF000CC010F
0101804D00070000E3E9F0E80038F0E1
E4000000000000000000000000000000
00000000000000000000000000000000
0000000000000000000000000000A8CB
""".replace("\n", "").replace(" ", "")

def test_unmask():    
    vec3 = bytearray(binascii.unhexlify(TVEC3))
    disarm._acb_speedup = _acb_speedup
    context = disarm.DisarmContext("0x0")
    context.disarm(vec3)
    hash = hashlib.sha256(vec3).hexdigest()
    print(binascii.hexlify(vec3))
    assert hash == "9d05c9475a6df68076d6e88bb94117f4cf405e5d01aeb32006a94cffa7168c67"

    vec3 = bytearray(binascii.unhexlify(TVEC3))
    disarm._acb_speedup = None
    context = disarm.DisarmContext("0x0")
    context.disarm(vec3)
    hash = hashlib.sha256(vec3).hexdigest()
    print(binascii.hexlify(vec3))
    assert hash == "9d05c9475a6df68076d6e88bb94117f4cf405e5d01aeb32006a94cffa7168c67"
