"""Strict boot-mode protocol, ported from the device-tested IOKit client."""
from dataclasses import dataclass
import struct
import time

VID, PID = 0x2dc8, 0x3208


class ProtocolError(RuntimeError):
    pass


def crc16(data):
    crc = 0xffff
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xa001 if crc & 1 else 0)
    return crc


@dataclass(frozen=True)
class Request:
    command: int
    address: int = 0
    length: int = 0
    total: int = 0
    payload: bytes = b''

    def packet(self):
        if self.length > 46 or (self.payload and len(self.payload) != self.length):
            raise ValueError('Invalid packet payload')
        packet = bytearray(64)
        packet[0] = 5
        struct.pack_into('<H', packet, 1, self.command)
        packet[17:17+len(self.payload)] = self.payload
        crc = 0 if self.command == 8 else crc16(packet[17:17+self.length])
        struct.pack_into('<HHII', packet, 5, self.length, crc, self.total, self.address)
        return bytes(packet)

    def decode(self, reply):
        if len(reply) < 6 or reply[:2] != b'\x00\x05' or struct.unpack_from('<H', reply, 4)[0] != self.command:
            return None  # Unrelated asynchronous report.
        if struct.unpack_from('<H', reply, 2)[0] != 0:
            raise ProtocolError(f'기기가 명령 {self.command}을 거부했습니다.')
        if self.command in (2, 3, 4):
            return b''  # These commands return a status-only ACK.
        if len(reply) != 64:
            raise ProtocolError('잘못된 응답 크기')
        length, checksum, total, address = struct.unpack_from('<HHII', reply, 6)
        expected = 4 if self.command == 8 else self.length
        expected_total = 4 if self.command == 8 else self.total
        if (length, total, address) != (expected, expected_total, self.address) or length > 46:
            raise ProtocolError('응답 주소 또는 길이가 일치하지 않습니다.')
        data = reply[18:18+length]
        if crc16(data) != checksum:
            raise ProtocolError('응답 CRC가 일치하지 않습니다.')
        if self.command == 8 and data != b'\x07\x60\x00\x00':
            raise ProtocolError('지원 대상 Ultimate Bluetooth 모델이 아닙니다.')
        return data


class HidTransport:
    """hidapi supplies native HID access on Windows and macOS, without custom drivers."""
    def __init__(self):
        self.device = None

    @staticmethod
    def enumerate():
        import hid
        # Deduplicate identical paths; do not select an arbitrary device.
        return list({d['path']: d for d in hid.enumerate(VID, PID)}.values())

    def open(self):
        import hid
        devices = self.enumerate()
        if len(devices) != 1:
            raise ProtocolError('부트모드 컨트롤러 한 대만 연결해 주세요.' if devices else '부트모드 기기를 찾지 못했습니다. L+R을 누른 채 USB로 연결해 주세요.')
        self.device = hid.device()
        try:
            self.device.open_path(devices[0]['path'])
        except Exception:
            self.close()
            raise
        return {k: devices[0].get(k) for k in ('vendor_id','product_id','product_string','serial_number')}

    def exchange(self, request):
        # hidapi requires a leading report ID 0 for unnumbered reports; the
        # actual 64-byte device payload is unchanged from the IOKit client.
        written = self.device.write(b'\x00' + request.packet())
        if written not in (64, 65):
            raise ProtocolError('USB 전송이 완료되지 않았습니다.')
        if request.command == 7:
            return b''
        deadline = time.monotonic() + (15 if request.command == 4 else 3)
        while time.monotonic() < deadline:
            reply = bytes(self.device.read(64, 100))
            if reply:
                result = request.decode(reply)
                if result is not None:
                    return result
        raise ProtocolError('기기 응답 시간이 초과됐습니다. 연결을 유지해 주세요.')

    def close(self):
        if self.device is not None:
            self.device.close()
            self.device = None
