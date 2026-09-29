"""Round-trip real C decoder/encoder against the P1.3 Python reference."""

import argparse
import random
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "hardware" / "protocol"))
from ar01_link import STATUS, decode_frame, encode_frame  # noqa: E402


def c_round_trip(cli, frame):
    result = subprocess.run([str(cli), frame.hex()], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"C rejected valid frame: {frame.hex()}")
    return bytes.fromhex(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cli", type=Path)
    args = parser.parse_args()
    rng = random.Random(0xA101)
    payloads = [
        (1, struct.pack("<ii", -15000, 15000)),
        (2, b""), (3, b""), (4, b""),
        (0x81, STATUS.pack(1234, -100, 200, 500, 600, 12000, 0, 1, 42)),
    ]
    for _ in range(50):
        payloads.append((1, struct.pack("<ii", rng.randint(-20000, 20000),
                                         rng.randint(-20000, 20000))))
    for index, (kind, payload) in enumerate(payloads):
        wire = encode_frame(kind, index * 1237 % 65536, payload)
        observed = c_round_trip(args.cli, wire)
        assert observed == wire
        assert decode_frame(observed) == (kind, index * 1237 % 65536, payload)
    bad = bytearray(encode_frame(1, 2, struct.pack("<ii", 1, 2)))
    bad[4] ^= 1
    result = subprocess.run([str(args.cli), bad.hex()], capture_output=True)
    assert result.returncode != 0
    print(f"C/Python protocol interoperability: {len(payloads)} valid + CRC fault PASS")


if __name__ == "__main__":
    main()
