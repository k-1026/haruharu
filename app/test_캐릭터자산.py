"""AI/외부 패키지 없이 투명 모션·원본 보존·프레임 간격을 확인한다."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
import zlib

ROOT = Path(__file__).parent / '담당자화면' / 'characters'


def gif_timing(data):
    at = 13 + (3 * (2 ** ((data[10] & 7) + 1)) if data[10] & 128 else 0)
    delays, delay = [], 100
    while at < len(data) and data[at] != 0x3b:
        marker = data[at]
        at += 1
        if marker == 0x21:
            kind = data[at]
            at += 1
            if kind == 0xf9:
                delay = max(10, struct.unpack_from('<H', data, at + 2)[0] * 10)
            while data[at]:
                at += data[at] + 1
            at += 1
        elif marker == 0x2c:
            packed = data[at + 8]
            at += 9 + (3 * 2 ** ((packed & 7) + 1) if packed & 128 else 0)
            at += 1  # LZW code size
            while data[at]:
                at += data[at] + 1
            at += 1
            delays.append(delay)
        else:
            raise AssertionError('잘못된 GIF 블록')
    return delays


def png_chunks(data):
    at = 8
    while at < len(data):
        length, = struct.unpack_from('>I', data, at)
        kind, body = data[at + 4:at + 8], data[at + 8:at + 8 + length]
        crc, = struct.unpack_from('>I', data, at + 8 + length)
        assert zlib.crc32(kind + body) == crc, 'PNG CRC 불일치'
        yield kind, body
        at += 12 + length


def first_frame_alpha(chunks, width, height):
    raw = zlib.decompress(b''.join(body for kind, body in chunks if kind == b'IDAT'))
    previous = bytearray(width * 4)
    alpha = []
    for y in range(height):
        at, stride = y * (width * 4 + 1), width * 4
        kind, row = raw[at], bytearray(raw[at + 1:at + 1 + stride])
        for x in range(stride):
            a, b, c = row[x - 4] if x >= 4 else 0, previous[x], previous[x - 4] if x >= 4 else 0
            p = a + b - c
            predictor = a if abs(p - a) <= abs(p - b) and abs(p - a) <= abs(p - c) else b if abs(p - b) <= abs(p - c) else c
            row[x] = (row[x] + [0, a, b, (a + b) // 2, predictor][kind]) & 255
        alpha.extend(row[3::4])
        previous = row
    return alpha


class 캐릭터자산시험(unittest.TestCase):
    def test_원본보존과_투명한_애니메이션의_프레임_시간을_유지한다(self):
        manifest = json.loads((ROOT / 'transparent/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['clips']), 6)
        for clip in manifest['clips']:
            with self.subTest(clip=clip['name']):
                original = (ROOT / (clip['name'] + '.gif')).read_bytes()
                self.assertEqual(hashlib.sha256(original).hexdigest(), clip['sourceSha256'])
                self.assertEqual(gif_timing(original), clip['durationMs'])
                data = (ROOT / 'transparent' / (clip['name'] + '.png')).read_bytes()
                self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
                chunks = list(png_chunks(data))
                header = next(body for kind, body in chunks if kind == b'IHDR')
                width, height, depth, color = struct.unpack_from('>IIBB', header)
                self.assertEqual((depth, color), (8, 6))
                self.assertEqual((width, height), tuple(manifest['crop'][2:]))
                count, plays = struct.unpack('>II', next(body for kind, body in chunks if kind == b'acTL'))
                self.assertEqual((count, plays), (len(clip['durationMs']), 0))
                frames = [body for kind, body in chunks if kind == b'fcTL']
                self.assertEqual(len(frames), count)
                self.assertEqual([round(struct.unpack_from('>HH', body, 20)[0] * 1000 / struct.unpack_from('>HH', body, 20)[1]) for body in frames], clip['durationMs'])
                sequence = [struct.unpack_from('>I', body)[0] for kind, body in chunks if kind in (b'fcTL', b'fdAT')]
                self.assertEqual(sequence, list(range(len(sequence))))
                alpha = first_frame_alpha(chunks, width, height)
                self.assertEqual([alpha[0], alpha[width - 1], alpha[-width], alpha[-1]], [0, 0, 0, 0])
                self.assertGreater(alpha.count(255), 10000)
                self.assertGreater(alpha.count(0), width * height // 2)


if __name__ == '__main__':
    unittest.main()
