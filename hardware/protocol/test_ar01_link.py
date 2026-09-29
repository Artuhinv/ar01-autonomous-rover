import binascii
import unittest

from ar01_link import (
    SPEED,
    STATUS,
    cobs_decode,
    cobs_encode,
    decode_frame,
    encode_frame,
    encode_speed,
)


class LinkTest(unittest.TestCase):
    def test_crc_standard_vector(self):
        self.assertEqual(binascii.crc_hqx(b"123456789", 0xFFFF), 0x29B1)

    def test_cobs_round_trip(self):
        for data in (b"", b"\x00", b"abc\x00def", bytes(range(256))):
            with self.subTest(data=data[:8]):
                self.assertEqual(cobs_decode(cobs_encode(data)), data)

    def test_speed_round_trip(self):
        kind, sequence, payload = decode_frame(encode_speed(65535, -15000, 15000))
        self.assertEqual((kind, sequence), (1, 65535))
        self.assertEqual(SPEED.unpack(payload), (-15000, 15000))

    def test_status_shape(self):
        payload = STATUS.pack(1234, -100, 200, 500, 600, 12000, 0, 1, 42)
        kind, sequence, observed = decode_frame(encode_frame(0x81, 19, payload))
        self.assertEqual((kind, sequence, STATUS.unpack(observed)),
                         (0x81, 19, STATUS.unpack(payload)))

    def test_corruption_rejected(self):
        frame = bytearray(encode_speed(2, 100, 200))
        frame[4] ^= 1
        with self.assertRaises(ValueError):
            decode_frame(bytes(frame))
        with self.assertRaises(ValueError):
            decode_frame(encode_speed(2, 100, 200)[:-1])
        with self.assertRaises(ValueError):
            decode_frame(encode_frame(9, 1))


if __name__ == "__main__":
    unittest.main()
