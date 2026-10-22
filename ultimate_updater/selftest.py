"""Offline bundle smoke test. Never imports HID or opens a device."""
from .firmware import PATCH, transform, sha
from .protocol import Request, crc16


def main():
    assert crc16(b'123456789') == 0x4b37
    probe = bytes((i*37+13)&255 for i in range(257*512+4))
    assert transform(transform(probe,encrypt=True)) == probe
    packet = Request(8,length=2,total=2).packet()
    assert len(packet)==64 and packet[:3]==b'\x05\x08\x00' and packet[7:9]==b'\0\0'
    assert len(bytes.fromhex(PATCH['append_hex'])) == PATCH['radio_offset']-PATCH['append_offset']
    assert PATCH['target_sha256'] == 'f8edd30b192b9faa5d29039328b0882b79d0094f7d1c2597d8c018117e6bf552'
    print('Offline bundle self-test passed. No device accessed.')
    return 0
