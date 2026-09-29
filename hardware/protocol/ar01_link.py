"""Host-side reference framing for the proposed AR-01 MCU link v1.

This is a protocol test oracle, not motor-control firmware.
"""

import binascii
import struct

MAGIC = 0xA1
VERSION = 1
MAX_DECODED = 64
HEADER = struct.Struct("<BBBBHB")
SPEED = struct.Struct("<ii")
STATUS = struct.Struct("<IqqHHHHBH")
CRC = struct.Struct("<H")


def cobs_encode(data):
    result = bytearray([0])
    code_index = 0
    code = 1
    for value in data:
        if value == 0:
            result[code_index] = code
            code_index = len(result)
            result.append(0)
            code = 1
        else:
            result.append(value)
            code += 1
            if code == 0xFF:
                result[code_index] = code
                code_index = len(result)
                result.append(0)
                code = 1
    result[code_index] = code
    return bytes(result)


def cobs_decode(data):
    if not data or 0 in data:
        raise ValueError("invalid COBS data")
    output = bytearray()
    index = 0
    while index < len(data):
        code = data[index]
        index += 1
        end = index + code - 1
        if end > len(data):
            raise ValueError("truncated COBS data")
        output.extend(data[index:end])
        index = end
        if code != 0xFF and index < len(data):
            output.append(0)
    return bytes(output)


def encode_frame(message_type, sequence, payload=b""):
    if not 0 <= sequence <= 0xFFFF:
        raise ValueError("sequence out of range")
    if not 0 <= message_type <= 0xFF:
        raise ValueError("message type out of range")
    if len(payload) > MAX_DECODED - HEADER.size - CRC.size:
        raise ValueError("payload too long")
    body = HEADER.pack(MAGIC, VERSION, message_type, 0, sequence, len(payload)) + payload
    body += CRC.pack(binascii.crc_hqx(body, 0xFFFF))
    return cobs_encode(body) + b"\x00"


def decode_frame(frame):
    if not frame.endswith(b"\x00") or frame.count(b"\x00") != 1:
        raise ValueError("frame must have one zero delimiter")
    body = cobs_decode(frame[:-1])
    if not HEADER.size + CRC.size <= len(body) <= MAX_DECODED:
        raise ValueError("invalid frame length")
    magic, version, message_type, flags, sequence, length = HEADER.unpack_from(body)
    if (magic, version, flags) != (MAGIC, VERSION, 0):
        raise ValueError("unsupported header")
    if len(body) != HEADER.size + length + CRC.size:
        raise ValueError("payload length mismatch")
    expected_crc = binascii.crc_hqx(body[:-CRC.size], 0xFFFF)
    if CRC.unpack_from(body, len(body) - CRC.size)[0] != expected_crc:
        raise ValueError("CRC mismatch")
    payload = body[HEADER.size:-CRC.size]
    allowed_lengths = {1: SPEED.size, 2: 0, 3: 0, 4: 0, 0x81: STATUS.size}
    if message_type not in allowed_lengths or length != allowed_lengths[message_type]:
        raise ValueError("unknown type or invalid payload length")
    return message_type, sequence, payload


def encode_speed(sequence, left_mrad_s, right_mrad_s):
    return encode_frame(1, sequence, SPEED.pack(left_mrad_s, right_mrad_s))
