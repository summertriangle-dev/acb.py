import struct

try:
    import _acb_speedup
except ImportError:
    _acb_speedup = None

SECTION_SIZES = {
    b"HCA\x00": 8,
    b"fmt\x00": 16,
    b"comp":    16,
    b"dec\x00": 12,
    b"vbr\x00": 8,
    b"ath\x00": 6,
    b"loop":    16,
    b"ciph":    6,
    b"rva\x00": 8,
    b"comm":    5,
    b"pad\x00": 4,
}

CHECKSUM_TABLE = (
    0x0000, 0x8005, 0x800F, 0x000A, 0x801B, 0x001E, 0x0014, 0x8011,
    0x8033, 0x0036, 0x003C, 0x8039, 0x0028, 0x802D, 0x8027, 0x0022,
    0x8063, 0x0066, 0x006C, 0x8069, 0x0078, 0x807D, 0x8077, 0x0072,
    0x0050, 0x8055, 0x805F, 0x005A, 0x804B, 0x004E, 0x0044, 0x8041,
    0x80C3, 0x00C6, 0x00CC, 0x80C9, 0x00D8, 0x80DD, 0x80D7, 0x00D2,
    0x00F0, 0x80F5, 0x80FF, 0x00FA, 0x80EB, 0x00EE, 0x00E4, 0x80E1,
    0x00A0, 0x80A5, 0x80AF, 0x00AA, 0x80BB, 0x00BE, 0x00B4, 0x80B1,
    0x8093, 0x0096, 0x009C, 0x8099, 0x0088, 0x808D, 0x8087, 0x0082,
    0x8183, 0x0186, 0x018C, 0x8189, 0x0198, 0x819D, 0x8197, 0x0192,
    0x01B0, 0x81B5, 0x81BF, 0x01BA, 0x81AB, 0x01AE, 0x01A4, 0x81A1,
    0x01E0, 0x81E5, 0x81EF, 0x01EA, 0x81FB, 0x01FE, 0x01F4, 0x81F1,
    0x81D3, 0x01D6, 0x01DC, 0x81D9, 0x01C8, 0x81CD, 0x81C7, 0x01C2,
    0x0140, 0x8145, 0x814F, 0x014A, 0x815B, 0x015E, 0x0154, 0x8151,
    0x8173, 0x0176, 0x017C, 0x8179, 0x0168, 0x816D, 0x8167, 0x0162,
    0x8123, 0x0126, 0x012C, 0x8129, 0x0138, 0x813D, 0x8137, 0x0132,
    0x0110, 0x8115, 0x811F, 0x011A, 0x810B, 0x010E, 0x0104, 0x8101,
    0x8303, 0x0306, 0x030C, 0x8309, 0x0318, 0x831D, 0x8317, 0x0312,
    0x0330, 0x8335, 0x833F, 0x033A, 0x832B, 0x032E, 0x0324, 0x8321,
    0x0360, 0x8365, 0x836F, 0x036A, 0x837B, 0x037E, 0x0374, 0x8371,
    0x8353, 0x0356, 0x035C, 0x8359, 0x0348, 0x834D, 0x8347, 0x0342,
    0x03C0, 0x83C5, 0x83CF, 0x03CA, 0x83DB, 0x03DE, 0x03D4, 0x83D1,
    0x83F3, 0x03F6, 0x03FC, 0x83F9, 0x03E8, 0x83ED, 0x83E7, 0x03E2,
    0x83A3, 0x03A6, 0x03AC, 0x83A9, 0x03B8, 0x83BD, 0x83B7, 0x03B2,
    0x0390, 0x8395, 0x839F, 0x039A, 0x838B, 0x038E, 0x0384, 0x8381,
    0x0280, 0x8285, 0x828F, 0x028A, 0x829B, 0x029E, 0x0294, 0x8291,
    0x82B3, 0x02B6, 0x02BC, 0x82B9, 0x02A8, 0x82AD, 0x82A7, 0x02A2,
    0x82E3, 0x02E6, 0x02EC, 0x82E9, 0x02F8, 0x82FD, 0x82F7, 0x02F2,
    0x02D0, 0x82D5, 0x82DF, 0x02DA, 0x82CB, 0x02CE, 0x02C4, 0x82C1,
    0x8243, 0x0246, 0x024C, 0x8249, 0x0258, 0x825D, 0x8257, 0x0252,
    0x0270, 0x8275, 0x827F, 0x027A, 0x826B, 0x026E, 0x0264, 0x8261,
    0x0220, 0x8225, 0x822F, 0x022A, 0x823B, 0x023E, 0x0234, 0x8231,
    0x8213, 0x0216, 0x021C, 0x8219, 0x0208, 0x820D, 0x8207, 0x0202
)

def checksum(buf: bytes):
    """
    Calculate the checksum of a block.
    """
    if _acb_speedup:
        return _acb_speedup.checksum_fast(buf)

    sum = 0
    for byte in buf:
        sum = ((sum << 8) ^ CHECKSUM_TABLE[(sum >> 8) ^ byte]) & 0xffff
    return sum

def _sub1_rollover(i: int) -> int:
    if i == 0:
        return 0xffffffff
    return i - 1

def _small_rng(seed: int) -> bytearray:
    a = ((seed & 1) << 3) | 0b0101
    c = (seed & 0xe) | 1
    seed >>= 4

    table = bytearray(16)
    for i in range(16):
        seed = (seed * a + c) & 0xf
        table[i] = seed
    return table

def _mix_header_key(kl, hk):
    k2p = (hk << 16) | (((hk ^ 0xffff) + 2) & 0xffff)
    return (kl * k2p) & 0xffffffffffffffff

class DisarmContext(object):
    KEY_TABLE_1: bytearray = None # type: ignore

    @classmethod
    def _init_table1(cls) -> bytearray:
        t = bytearray(256)
        t[0x00] = 0
        t[0xff] = 0xff
        seed = 0

        for i in range(1, 255):
            seed = (seed * 13 + 11) & 0xff
            if seed == 0 or seed == 0xff:
                seed = (seed * 13 + 11) & 0xff
            t[i] = seed

        return t

    def __init__(self, keyspec: str, header_key: int = None):
        if "," in keyspec:
            keya_, keyb_ = keyspec.split(",")
            keya = int(keya_, 16)
            keyb = int(keyb_, 16)

            if header_key:
                keylong = _mix_header_key(keya | (keyb << 32), header_key)
                keya = keylong & 0xffffffff
                keyb = (keylong >> 32) & 0xffffffff
        else:
            keylong = int(keyspec, 16)
            if header_key:
                keylong = _mix_header_key(keylong, header_key)

            keya = keylong & 0xffffffff
            keyb = (keylong >> 32) & 0xffffffff

        self.keya = keya
        self.keyb = keyb
        self._init_tables()

    def _init_tables(self):
        if self.__class__.KEY_TABLE_1 is None:
            self.__class__.KEY_TABLE_1 = self._init_table1()

        self.key_table_2 = self._init_table2()

    def _init_table2(self) -> bytearray:
        keya = self.keya
        keyb = self.keyb

        if keya == 0:
            keyb = _sub1_rollover(keyb)
        keya = _sub1_rollover(keya)

        stage1 = bytearray(8)
        for i in range(7):
            stage1[i] = keya & 0xff
            keya = ((keya >> 8) | (keyb << 24)) & 0xffffffff
            keyb >>= 8

        s2_ri = (1, 2, 3, 4, 5, 6, 1)
        s2_li = (0, 6, 1, 2, 3, 4, 5)
        stage2 = bytearray(16)

        for i in range(0, 16, 3):
            stage2[i] = stage1[i // 3 + 1]

        for i in range(1, 16, 3):
            j = i // 3 + 1
            stage2[i] = stage1[j] ^ stage1[s2_li[j]]

        for i in range(2, 16, 3):
            j = i // 3 + 2
            stage2[i] = stage1[j] ^ stage1[s2_ri[j]]

        stage3 = bytearray(256)
        high = _small_rng(stage1[0])
        for i in range(16):
            base = 16 * i
            low = _small_rng(stage2[i])
            hi = high[i] << 4
            for j in range(16):
                stage3[base + j] = hi | low[j]

        key_table_2 = bytearray(256)
        key_table_2[0x00] = 0
        key_table_2[0xff] = 0xff
        srci = 0x11
        for i in range(1, 255):
            while stage3[srci] in (0x0, 0xff):
                srci = (srci + 0x11) & 0xff

            key_table_2[i] = stage3[srci]
            srci = (srci + 0x11) & 0xff

        return key_table_2

    def disarm(self, buf: bytearray, no_unmask: bool=False):
        """
        Remove encryption from a full HCA file in buf.
        - no_unmask: If true, this will leave section names alone, which means
          files will not be decodable by ffmpeg.
        """
        magic = buf[:4]
        masked = True if magic[0] & 0x80 else False
        header_size = struct.unpack(">H", buf[6:8])[0]

        if not no_unmask:
            self.unmask_header(buf, header_size)
            masked = False

        try:
            comp_seg = buf.index(b"\xe3\xef\xed\xf0" if masked else b"comp", 0, header_size)
        except ValueError:
            try:
                comp_seg = buf.index(b"\xe4\xe5\xe3\x00" if masked else b"dec\x00", 0, header_size)
            except ValueError:
                raise ValueError("cannot find a segment containing the block size")

        try:
            ciph_seg = buf.index(b"\xe3\xe9\xf0\xe8" if masked else b"ciph", 0, header_size)
        except ValueError:
            return

        try:
            fmt_seg = buf.index(b"\xe6\xed\xf4\x00" if masked else b"fmt\x00", 0, header_size)
        except ValueError:
            raise ValueError("cannot find the fmt segment")

        block_cnt = struct.unpack(">I", buf[fmt_seg + 8:fmt_seg + 12])[0]
        block_size = struct.unpack(">H", buf[comp_seg + 4:comp_seg + 6])[0]
        ciph_type = struct.unpack(">H", buf[ciph_seg + 4:ciph_seg + 6])[0]

        if ciph_type == 0:
            return

        self.disarm_blocks(buf, header_size, block_cnt, block_size, ciph_type)
        buf[ciph_seg + 4:ciph_seg + 6] = b"\x00\x00"

        end = header_size - 2
        if _acb_speedup:
            _acb_speedup.checksum_block_fast(memoryview(buf)[:header_size])
        else:
            buf[end:end + 2] = checksum(memoryview(buf)[:end]).to_bytes(2, "big")

    def unmask_header(self, buf: bytearray, header_size: int):
        """
        Remove masking of section names from the HCA header.
        This does not update the checksum or modify any section content.
        """
        base = 0
        while base < header_size:
            tag = bytes(x & 0x7f for x in buf[base:base + 4])
            buf[base:base + 4] = tag

            if tag == b"pad\x00":
                break
            if tag == b"comm":
                base += buf[base + 4]

            base += SECTION_SIZES.get(tag, 4)

    def disarm_blocks(self, buf: bytearray, from_pos: int, block_count: int, block_size: int, ciph_type: int):
        """
        Remove encryption from one or more HCA blocks. buf should be at least 
        from_pos + (block_size * block_count) bytes long.

        - from_pos: Start of the first block as an offset into buf.
        - block_count: Number of blocks to decrypt.
        - block_size: Size of each block (get this from the HCA header)
        - ciph_type: Cipher type (get this from the HCA header)
        """
        if ciph_type == 0:
            return
        elif ciph_type == 1:
            usetable = self.KEY_TABLE_1
        elif ciph_type == 56:
            usetable = self.key_table_2
        else:
            raise ValueError("unknown cipher type")
        
        self.disarm_actual(buf, from_pos, block_count, block_size, usetable)

    def disarm_actual(self, buf: bytearray, frompos: int, blockcnt: int, blocksize: int, usetable: bytearray):
        """
        Do not call this method. If you were already using this, update your code to 
        use disarm_blocks().
        """
        base = frompos
        stop = frompos + (blocksize * blockcnt)
        while base < stop:
            if _acb_speedup:
                _acb_speedup.disarm_block_fast(memoryview(buf)[base:base + blocksize], usetable)
            else:
                for i in range(base, base + blocksize - 2):
                    buf[i] = usetable[buf[i]]

                end = base + blocksize - 2
                buf[end:end + 2] = checksum(memoryview(buf)[base:end]).to_bytes(2, "big")

            base += blocksize
