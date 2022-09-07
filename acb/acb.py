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
import struct
import itertools
import os
import re
from collections import namedtuple as T
from typing import Optional, Union, BinaryIO, Tuple, List, Callable

from .utf import UTFTable, R
from .disarm import DisarmContext

WAVEFORM_ENCODE_TYPE_ADX          = 0
WAVEFORM_ENCODE_TYPE_HCA          = 2
WAVEFORM_ENCODE_TYPE_VAG          = 7
WAVEFORM_ENCODE_TYPE_ATRAC3       = 8
WAVEFORM_ENCODE_TYPE_BCWAV        = 9
WAVEFORM_ENCODE_TYPE_NINTENDO_DSP = 13

wave_type_ftable = {
    WAVEFORM_ENCODE_TYPE_ADX          : ".adx",
    WAVEFORM_ENCODE_TYPE_HCA          : ".hca",
    WAVEFORM_ENCODE_TYPE_VAG          : ".vag",
    WAVEFORM_ENCODE_TYPE_ATRAC3       : ".at3",
    WAVEFORM_ENCODE_TYPE_BCWAV        : ".bcwav",
    WAVEFORM_ENCODE_TYPE_NINTENDO_DSP : ".dsp"}

track_t = T("track_t", ("cue_id", "name", "memory_wav_id", "external_wav_id", "enc_type", "is_stream"))

class TrackList(object):
    def __init__(self, utf):
        cue_handle = io.BytesIO(utf.rows[0]["CueTable"])
        nam_handle = io.BytesIO(utf.rows[0]["CueNameTable"])
        wav_handle = io.BytesIO(utf.rows[0]["WaveformTable"])
        syn_handle = io.BytesIO(utf.rows[0]["SynthTable"])

        cues = UTFTable(cue_handle, encoding=utf.encoding)
        nams = UTFTable(nam_handle, encoding=utf.encoding)
        wavs = UTFTable(wav_handle, encoding=utf.encoding)
        syns = UTFTable(syn_handle, encoding=utf.encoding)

        self.tracks: List[track_t] = []

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
    def __init__(self, file, *, encoding=None):
        buf = R(file, encoding=encoding)

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

AnyFile = Union[str, os.PathLike, BinaryIO]
Uninitialized = object()

def _get_file_obj(name: AnyFile) -> Tuple[BinaryIO, bool]:
    if isinstance(name, (str, os.PathLike)):
        return open(name, "rb"), True
    else:
        return name, False

class ACBFile(object):
    """ Represents an ACB file.

        You should call the close() method to release the underlying file objects
        when finished, or use the object as a context manager.
        Tracks can be accessed using .track_list together with get_track_data().

        Constructor arguments:
        - acb_file: Path to the file, or an open file object in binary mode.
        - extern_awb: Path to the streaming AWB file, if needed.
        - hca_keys: HCA keys in string format. Can be one of:
            "0xLOWBYTES,0xHIGHBYTES", "0xHIGHBYTESLOWBYTES", or None.
            "0xLOWBYTES,0xHIGHBYTES" is equivalent to invoking hca_decoder
            with arguments "-a LOWBYTES -b HIGHBYTES".
            If None, HCA files will not be decrypted.
        - encoding: String encoding to use when reading the file. If this is
            not passed, we'll try reading it as Shift-JIS first (for backwards
            compatibility reasons), and then UTF-8, before giving up. If an 
            encoding is explicitly passed, only that encoding will be used. 
    """
    def __init__(self, acb_file: AnyFile, extern_awb: Optional[AnyFile] = None, hca_keys: Optional[str] = None, encoding: str = None):
        self.acb_handle, self.acb_handle_owned = _get_file_obj(acb_file)
        
        if extern_awb is None:
            self.awb_handle = None
            self.awb_handle_owned = False
        else:
            self.awb_handle, self.awb_handle_owned = _get_file_obj(extern_awb)

        self.encoding = encoding or "sjis"
        try:
            utf = UTFTable(self.acb_handle, encoding=encoding or "sjis")
            self.track_list = TrackList(utf)
        except UnicodeDecodeError:
            if encoding is None:
                self.encoding = "utf-8"
                utf = UTFTable(self.acb_handle, encoding="utf-8")
                self.track_list = TrackList(utf)
            else:
                raise

        if len(utf.rows[0]["AwbFile"]) > 0:
            self.embedded_awb = AFSArchive(io.BytesIO(utf.rows[0]["AwbFile"]), encoding=self.encoding)
        else:
            self.embedded_awb = None # type: ignore

        if self.awb_handle:
            self.external_awb = AFSArchive(self.awb_handle, encoding=self.encoding)
        else:
            self.external_awb = None # type: ignore

        self.hca_keys = hca_keys
        self.embedded_disarm: Optional[DisarmContext] = Uninitialized # type: ignore
        self.external_disarm: Optional[DisarmContext] = Uninitialized # type: ignore
        
        self.closed = False
    
    def get_embedded_disarm(self) -> Optional[DisarmContext]:
        if self.embedded_disarm is Uninitialized:
            if self.hca_keys:
                self.embedded_disarm = DisarmContext(self.hca_keys, self.embedded_awb.mix_key)
            else:
                self.embedded_disarm = None

        return self.embedded_disarm
    
    def get_external_disarm(self) -> Optional[DisarmContext]:
        if self.external_disarm is Uninitialized:
            if self.hca_keys:
                self.external_disarm = DisarmContext(self.hca_keys, self.external_awb.mix_key)
            else:
                self.external_disarm = None
        return self.external_disarm

    def get_track_data(self, track: track_t, disarm: Optional[bool] = None, unmask: bool = True) -> bytearray:
        """ Gets encoded audio data as a bytearray.

            Arguments:
            - track: The track to get data for, from .track_list.
            - disarm: Whether to decrypt HCA data before returning it.
                The default action is to decrypt if hca_keys were passed when creating
                the ACBFile. You can pass False to skip decryption, or True to force
                decryption. 
                ValueError is raised you force decryption and keys were not passed.
            - unmask: Whether to remove XOR masking from HCA header tags. 
                This only has an effect if decryption is enabled, whether implicitly or
                explicitly.
        """
        if self.closed:
            raise ValueError("ACBFile is closed")

        if track.is_stream:
            buf = self.external_awb.file_data_for_cue_id(track.external_wav_id, rw=True)
            disarmer = self.get_external_disarm()
        else:
            buf = self.embedded_awb.file_data_for_cue_id(track.memory_wav_id, rw=True)
            disarmer = self.get_embedded_disarm()

        if disarm is True and not disarmer:
            raise ValueError(
                "Disarm was explicitly requested, but no keys were provided. "
                "Either remove the disarm= argument from the call to get_track_data, "
                "or provide keys using the hca_keys= argument to ACBFile."
            )
    
        if disarm is None:
            disarm = (disarmer is not None)

        if disarm and disarmer:
            disarmer.disarm(buf, not unmask)

        return buf

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        """ Close any open files held by ACBFile. If you passed file objects
            instead of paths when creating the ACBFile instance, they will
            not be closed.

            Can be called multiple times; subsequent calls will have no effect.
        """
        if self.acb_handle_owned:
            self.acb_handle.close()
            self.acb_handle_owned = False
        if self.awb_handle_owned:
            self.awb_handle.close()
            self.awb_handle_owned = False
        self.closed = True

    def __del__(self):
        self.close()


def find_awb(path):
    if re.search(r"\.acb$", path):
        awb_path = re.sub(r"\.acb$", ".awb", path)
        if os.path.exists(awb_path):
            return awb_path

def name_gen_default(track):
    return "{0}{1}".format(track.name, wave_type_ftable.get(track.enc_type, track.enc_type))

def extract_acb(
    acb_file: AnyFile,
    target_dir: str,
    extern_awb: Optional[AnyFile] = None,
    hca_keys: Optional[str] = None,
    name_gen: Callable[[track_t], str] = name_gen_default,
    no_unmask: bool = False,
    encoding: Optional[str] = None
):
    """ Oneshot file extraction API. Dumps all tracks from a file into the
        named output directory.

        Arguments:
        - acb_file: Path to the file, or an open file object in binary mode.
        - target_dir: Path to the destination directory. Must already exist.
        - extern_awb: Path to the streaming AWB file, if needed.
        - hca_keys: Same as ACBFile's hca_keys argument.
        - name_gen: A callable taking the track_t object and returning a 
            destination filename. Should not return absolute paths, as
            they will be prefixed with the target_dir.
        - no_unmask: See ACBFile.get_track_data's unmask argument. For 
            compatibility reasons, the meaning of this flag is reversed;
            i.e. True will result in unmasking being disabled.
        - encoding: Encoding used for track names. See ACBFile's docstring
            for behaviour when this argument is None/omitted. 
    """
    if isinstance(acb_file, str) and extern_awb is None:
        extern_awb = find_awb(acb_file)

    with ACBFile(acb_file, extern_awb=extern_awb, hca_keys=hca_keys, encoding=encoding) as acb:
        for track in acb.track_list.tracks:
            name = name_gen(track)

            with open(os.path.join(target_dir, name), "wb") as out_file:
                out_file.write(acb.get_track_data(track, unmask=not no_unmask))
