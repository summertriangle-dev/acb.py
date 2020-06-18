#!/usr/bin/env python3
# acb.py: For all your ACB extracting needs

# Copyright (c) 2016, The Holy Constituency of the Summer Triangle.
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# This program is based on code from VGMToolbox.
# Copyright (c) 2009
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

import io
import math
import struct
import sys
import itertools
import os
import re
from collections import namedtuple as T

try:
    from .utf import UTFTable, R
    from .disarm import DisarmContext
except ImportError:
    from utf import UTFTable, R
    from disarm import DisarmContext

WAVEFORM_ENCODE_TYPE_ADX          = 0
WAVEFORM_ENCODE_TYPE_HCA          = 2
WAVEFORM_ENCODE_TYPE_VAG          = 7
WAVEFORM_ENCODE_TYPE_ATRAC3       = 8
WAVEFORM_ENCODE_TYPE_BCWAV        = 9
WAVEFORM_ENCODE_TYPE_NINTENDO_DSP = 13

wave_type_ftable = {
    WAVEFORM_ENCODE_TYPE_ADX          : ".adx",
    WAVEFORM_ENCODE_TYPE_HCA          : ".hca",
    WAVEFORM_ENCODE_TYPE_VAG          : ".at3",
    WAVEFORM_ENCODE_TYPE_ATRAC3       : ".vag",
    WAVEFORM_ENCODE_TYPE_BCWAV        : ".bcwav",
    WAVEFORM_ENCODE_TYPE_NINTENDO_DSP : ".dsp"}

track_t = T("track_t", ("cue_id", "name", "memory_wav_id", "external_wav_id", "enc_type", "is_stream"))

class TrackList(object):
    def __init__(self, utf):
        cue_handle = io.BytesIO(utf.rows[0]["CueTable"])
        nam_handle = io.BytesIO(utf.rows[0]["CueNameTable"])
        wav_handle = io.BytesIO(utf.rows[0]["WaveformTable"])
        syn_handle = io.BytesIO(utf.rows[0]["SynthTable"])

        cues = UTFTable(cue_handle)
        nams = UTFTable(nam_handle)
        wavs = UTFTable(wav_handle)
        syns = UTFTable(syn_handle)

        self.tracks = []

        name_map = {}
        for row in nams.rows:
            name_map[row["CueIndex"]] = row["CueName"]

        for ind, row in enumerate(cues.rows):
            if row["ReferenceType"] not in {3, 8}:
                raise RuntimeError("ReferenceType {0} not implemented.".format(row["ReferenceType"]))

            r_data = syns.rows[row["ReferenceIndex"]]["ReferenceItems"]
            a, b = struct.unpack(">HH", r_data)

            wav_id = wavs.rows[b].get("Id")
            if wav_id is None:
                wav_id = wavs.rows[b]["MemoryAwbId"]
            extern_wav_id = wavs.rows[b]["StreamAwbId"]
            enc = wavs.rows[b]["EncodeType"]
            is_stream = wavs.rows[b]["Streaming"]

            self.tracks.append(track_t(row["CueId"], name_map.get(ind, "UNKNOWN"), wav_id,
                extern_wav_id, enc, is_stream))

def align(n):
    def _align(number):
        return (number + n - 1) & ~(n - 1)
    return _align

afs2_file_ent_t = T("afs2_file_ent_t", ("cue_id", "offset", "size"))

class AFSArchive(object):
    def __init__(self, file):
        buf = R(file)

        magic = buf.uint32_t()
        if magic != 0x41465332:
            raise ValueError("bad magic")

        version = buf.bytes(4)
        file_count = buf.le_uint32_t()

        if version[0] >= 0x02:
            self.alignment = buf.le_uint16_t()
            self.mix_key = buf.le_uint16_t()
        else:
            self.alignment = buf.le_uint32_t()
            self.mix_key = None

        #print("afs2:", file_count, "files in ar")
        #print("afs2: aligned to", self.alignment, "bytes")

        self.offset_size = version[1]
        self.offset_mask = int("FF" * self.offset_size, 16)
        #print("afs2: a file offset is", self.offset_size, "bytes")

        self.files = []
        self.create_file_entries(buf, file_count)
        self.src = buf

    def create_file_entries(self, buf, file_count):
        buf.seek(0x10)
        read_cue_ids = struct.Struct("<" + ("H" * file_count))
        if self.offset_size == 2:
            read_raw_offs = struct.Struct("<" + ("H" * (file_count + 1)))
        else:
            read_raw_offs = struct.Struct("<" + ("I" * (file_count + 1)))

        # read all in one go
        cue_ids = buf.struct(read_cue_ids)
        raw_offs = buf.struct(read_raw_offs)
        # apply the mask
        unaligned_offs = tuple(map(lambda x: x & self.offset_mask, raw_offs))
        aligned_offs = tuple(map(align(self.alignment), unaligned_offs))
        offsets_for_length_calculating = unaligned_offs[1:]
        lengths = itertools.starmap(
            lambda my_offset, next_offset: next_offset - my_offset,
            zip(aligned_offs, offsets_for_length_calculating))

        self.files = list(itertools.starmap(afs2_file_ent_t, zip(cue_ids, aligned_offs, lengths)))

    def file_data_for_cue_id(self, cue_id, rw=False):
        for f in self.files:
            if f.cue_id == cue_id:
                if rw:
                    buf = bytearray(f.size)
                    self.src.bytesinto(buf, at=f.offset)
                    return buf
                else:
                    return self.src.bytes(f.size, at=f.offset)
        else:
            raise ValueError("id {0} not found in archive".format(cue_id))

def find_awb(path):
    return re.sub(r"\.acb$", ".awb", path)

def name_gen_default(track):
     return "{0}{1}".format(track.name, wave_type_ftable.get(track.enc_type, track.enc_type))

def extract_acb(acb_file, target_dir, extern_awb=None, hca_keys=None, name_gen=name_gen_default, no_unmask=False):
    if isinstance(acb_file, str):
        with open(acb_file, "rb") as _acb_file:
            utf = UTFTable(_acb_file)
    else:
        utf = UTFTable(acb_file)

    cue = TrackList(utf)

    disarmer_mem = None
    disarmer_ext = None
    memory_data_source = None
    extern_data_source = None
    external_awb = None

    if len(utf.rows[0]["AwbFile"]) > 0:
        embedded_awb = io.BytesIO(utf.rows[0]["AwbFile"])
        memory_data_source = AFSArchive(embedded_awb)

    if any(track.is_stream for track in cue.tracks):
        extern_name = extern_awb or find_awb(acb_file)
        try:
            external_awb = open(extern_name, "rb")
        except FileNotFoundError:
            print("Error: At least one track requests streaming, but an external AWB could not be found.",
                file=sys.stderr)
            print("Specify the external AWB with --awb.",
                file=sys.stderr)
            sys.exit(1)
        extern_data_source = AFSArchive(external_awb)

    if hca_keys:
        if memory_data_source:
            disarmer_mem = DisarmContext(hca_keys, memory_data_source.mix_key)
        if extern_data_source:
            disarmer_ext = DisarmContext(hca_keys, extern_data_source.mix_key)

    for track in cue.tracks:
        print(track)
        name = name_gen(track)

        with open(os.path.join(target_dir, name_gen(track)), "wb") as named_out_file:
            if track.is_stream:
                wid = track.external_wav_id
                data_source = extern_data_source
                disarmer = disarmer_ext
            else:
                wid = track.memory_wav_id
                data_source = memory_data_source
                disarmer = disarmer_mem

            if hca_keys:
                hca_buf = data_source.file_data_for_cue_id(wid, rw=True)
                disarmer.disarm(hca_buf, no_unmask)
                named_out_file.write(hca_buf)
            else:
                named_out_file.write(data_source.file_data_for_cue_id(wid))

    if external_awb:
        external_awb.close()

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--disarm-with", help="decrypt HCAs with provided keys")
    parser.add_argument("--awb", help="use file as the external AWB")
    parser.add_argument("--no-unmask", action="store_true", default=False,
        help="don't unmask segment names (requires --disarm-with)")
    parser.add_argument("acb_file", help="input ACB file")
    parser.add_argument("output_dir", help="directory to place output files in")

    args = parser.parse_args()

    os.makedirs(args.output_dir, 0o755, exist_ok=True)
    extract_acb(args.acb_file, args.output_dir, args.awb, args.disarm_with, no_unmask=args.no_unmask)

if __name__ == '__main__':
    main()
