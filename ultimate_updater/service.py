"""Transactional install workflow. No retries, reset only after full verification."""
from datetime import datetime, timezone
from pathlib import Path
import json
import struct
import uuid

from .firmware import (APP_BASE, APP_SIZE, PEER_BASE, VERSION_ADDRESS,
                       atomic_write, identify_image, sha, transform)
from .protocol import Request, ProtocolError


class Cancelled(RuntimeError):
    pass


class Installer:
    def __init__(self, transport, backup_root, progress=lambda *args: None, cancelled=lambda: False):
        self.transport = transport
        self.backup_root = Path(backup_root)
        self.progress = progress
        self.cancelled = cancelled
        self.writing = False
        self.directory = None
        self.record = {}

    def emit(self, label, percent):
        self.progress(label, percent, self.writing)
        if not self.writing and self.cancelled():
            raise Cancelled('설치 전에 취소했습니다. 기기는 변경되지 않았습니다.')

    def read(self, address, length, label, start, span):
        result = bytearray()
        for offset in range(0, length, 40):
            n = min(40, length-offset)
            result.extend(self.transport.exchange(Request(5, address+offset, n, n)))
            if offset % 800 == 0 or offset+n == length:
                self.emit(label, start+int(span*(offset+n)/length))
        return bytes(result)

    def save_record(self):
        atomic_write(self.directory/'backup.json', json.dumps(self.record, ensure_ascii=False, indent=2).encode())

    def backup(self, identity):
        name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
        self.directory = self.backup_root/name
        self.directory.mkdir(parents=True, exist_ok=False)
        self.record = {'schema': 1, 'device': identity, 'created_at': name,
                       'status': 'reading', 'app_address': APP_BASE, 'peer_address': PEER_BASE}
        self.save_record()
        version = self.read(VERSION_ADDRESS, 4, '현재 버전 확인', 4, 1)
        app = self.read(APP_BASE, APP_SIZE, '기존 펌웨어 백업', 5, 21)
        peer = self.read(PEER_BASE, 4096, '페어링 정보 백업', 26, 4)
        for filename, data in [('app.bin',app),('peer.bin',peer),('version.bin',version)]:
            atomic_write(self.directory/filename, data)
        self.record.update(status='backed_up', version=struct.unpack('<I',version)[0],
                           app_bytes=len(app), app_sha256=sha(app), peer_sha256=sha(peer),
                           image=identify_image(app))
        self.save_record()
        # A successful fsync and independent reread are required before erase.
        if (self.directory/'app.bin').read_bytes() != app or (self.directory/'peer.bin').read_bytes() != peer:
            raise OSError('백업 파일 검증에 실패했습니다.')
        return app, peer

    def install(self, target, version=111, recovery=False):
        if len(target) != APP_SIZE or not identify_image(target) or version not in (109,110,111):
            raise ValueError('검증되지 않은 설치 이미지입니다.')
        payload = transform(target, encrypt=True)
        if transform(payload) != target:
            raise ValueError('펌웨어 암호화 검증 실패')
        try:
            self.emit('부트모드 기기 확인', 2)
            identity = self.transport.open()
            self.transport.exchange(Request(8, length=2, total=2))
            previous, peer = self.backup(identity)
            if not recovery and not identify_image(previous):
                raise ProtocolError('현재 펌웨어가 지원 목록과 다릅니다. 백업만 완료했으며 설치하지 않았습니다.')
            self.emit('백업 완료 · 설치 준비', 30)
            self.record.update(target_sha256=sha(target), target_version=version, recovery=recovery, status='writing')
            self.save_record()
            # Do not allow cancellation after the first destructive command.
            self.writing = True
            self.emit('펌웨어 영역 준비 · USB 연결 유지', 31)
            self.transport.exchange(Request(4, APP_BASE, total=len(target)))
            self.transport.exchange(Request(4, VERSION_ADDRESS, total=32))
            for offset in range(0,len(payload),46):
                chunk = payload[offset:offset+46]
                self.transport.exchange(Request(3, APP_BASE+offset,len(chunk),len(payload),chunk))
                if offset % 920 == 0:
                    self.emit('새 펌웨어 설치 · USB 연결 유지',32+int(37*(offset+len(chunk))/len(payload)))
            v = struct.pack('<I',version)
            self.transport.exchange(Request(2, VERSION_ADDRESS,4,4,v))
            post = self.read(APP_BASE,len(target),'설치된 펌웨어 전체 검증',70,25)
            atomic_write(self.directory/'readback.bin', post)
            if post != target:
                raise ProtocolError('설치 후 검증 실패. 연결을 유지하고 이전 백업으로 복구해 주세요.')
            confirmed = self.read(VERSION_ADDRESS,4,'버전 검증',95,1)
            if confirmed != v:
                raise ProtocolError('설치 후 버전이 일치하지 않습니다. 연결을 유지해 주세요.')
            # Verify that app updates did not overwrite the saved peer sector.
            peer_after = self.read(PEER_BASE,4096,'페어링 정보 보존 확인',96,3)
            if peer_after != peer:
                raise ProtocolError('페어링 영역이 변경되었습니다. 리셋하지 않았습니다. 백업을 보존해 주세요.')
            self.record.update(status='verified', readback_sha256=sha(post), peer_preserved=True)
            self.save_record()
            self.transport.exchange(Request(7))
            self.record.update(status='complete', reset_sent=True)
            self.save_record()
            self.emit('설치 완료',100)
            return self.directory
        except Exception as error:
            if self.directory:
                self.record.update(status='failed', error=str(error), erase_may_have_started=self.writing)
                self.save_record()
            raise
        finally:
            self.transport.close()


def load_backup(path):
    path = Path(path)
    record = json.loads(path.read_text())
    data = (path.parent/'app.bin').read_bytes()
    version = (path.parent/'version.bin').read_bytes()
    if record.get('schema') != 1 or record.get('app_address') != APP_BASE:
        raise ValueError('지원하는 백업 형식이 아닙니다.')
    if len(data) != APP_SIZE or sha(data) != record.get('app_sha256') or not identify_image(data):
        raise ValueError('백업 펌웨어가 손상됐거나 지원하는 버전이 아닙니다.')
    if len(version) != 4 or struct.unpack('<I',version)[0] != record.get('version'):
        raise ValueError('백업 버전 정보가 일치하지 않습니다.')
    return data, record['version']
