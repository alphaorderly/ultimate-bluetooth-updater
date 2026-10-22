import json
from pathlib import Path
import struct
import tempfile
import types
import unittest
from unittest.mock import patch

from ultimate_updater import firmware as fw
from ultimate_updater.protocol import Request, ProtocolError, HidTransport, crc16
from ultimate_updater.service import Installer, load_backup, Cancelled


def reply(request,data):
    result = bytearray(64)
    result[1]=5
    struct.pack_into('<H',result,4,request.command)
    n=len(data)
    struct.pack_into('<HHII',result,6,n,crc16(data),n,request.address)
    result[18:18+n]=data
    return bytes(result)


class Simulator:
    def __init__(self, app):
        self.app=app; self.peer=bytes(i%251 for i in range(4096)); self.version=struct.pack('<I',111)
        self.calls=[]; self.encrypted=bytearray(); self.fail=None; self.corrupt=False; self.closed=False

    def open(self):
        return {'vendor_id':0x2dc8,'product_id':0x3208,'serial_number':'synthetic'}

    def close(self):
        self.closed=True

    def exchange(self,r):
        self.calls.append(r)
        assert len(r.packet())==64
        if self.fail==r.command:
            raise ProtocolError('Injected transport failure')
        if r.command==8:
            return r.decode(reply(r,b'\x07\x60\0\0'))
        if r.command==5:
            if r.address==fw.VERSION_ADDRESS: data=self.version
            elif fw.PEER_BASE<=r.address<fw.PEER_BASE+4096:
                offset=r.address-fw.PEER_BASE;data=self.peer[offset:offset+r.length]
            else:
                offset=r.address-fw.APP_BASE
                assert 0<=offset<fw.APP_SIZE
                data=self.app[offset:offset+r.length]
                if self.corrupt and self.encrypted and offset==0:data=bytes([data[0]^1])+data[1:]
            return r.decode(reply(r,data))
        if r.command==4:
            assert (r.address,r.total) in [(fw.APP_BASE,fw.APP_SIZE),(fw.VERSION_ADDRESS,32)]
            if r.address==fw.APP_BASE:self.app=b'\xff'*fw.APP_SIZE
        elif r.command==3:
            assert r.address==fw.APP_BASE+len(self.encrypted) and r.total==fw.APP_SIZE
            self.encrypted.extend(r.payload)
            if len(self.encrypted)==fw.APP_SIZE:self.app=fw.transform(self.encrypted)
        elif r.command==2:self.version=r.payload
        elif r.command==7:return b''
        else:raise AssertionError(r)
        return r.decode(reply(r,b''))


class ProtocolTests(unittest.TestCase):
    def test_packet_matches_original_iokit_layout(self):
        r=Request(5,0x1017040,4,4)
        self.assertEqual(r.packet().hex(),'05050000000400002404000000407001010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000')

    def test_bad_read_fields_crc_and_pid_rejected(self):
        r=Request(5,fw.APP_BASE,4,4);good=reply(r,b'abcd')
        self.assertEqual(r.decode(good),b'abcd')
        for offset in [2,6,8,10,14,18]:
            bad=bytearray(good);bad[offset]^=1
            with self.assertRaises(ProtocolError):r.decode(bytes(bad))
        with self.assertRaises(ProtocolError):Request(8,length=2,total=2).decode(reply(Request(8),b'\x08\x60\0\0'))
        self.assertIsNone(r.decode(b'unrelated'))

    def test_transform_blocks_and_schedule_wrap(self):
        data=bytes((i*7)&255 for i in range(257*512))
        self.assertEqual(fw.transform(fw.transform(data,True)),data)
        with self.assertRaises(ValueError):fw.transform(b'x')

    def test_unknown_source_and_dirty_image_tail_rejected(self):
        with self.assertRaises(ValueError):fw.compose(b'bad',b'bad')
        with patch.object(fw,'KNOWN',[{'bytes':4,'sha256':fw.sha(b'abcd'),'name':'test'}]):
            self.assertEqual(fw.identify_image(b'abcd\xff'),'test')
            self.assertIsNone(fw.identify_image(b'abcd\0'))

    def test_hid_report_id_framing_and_ambiguous_device_rejection(self):
        r=Request(8,length=2,total=2)
        class Device:
            sent=None
            def open_path(self,path):self.path=path
            def write(self,data):self.sent=data;return len(data)
            def read(self,size,timeout):return reply(r,b'\x07\x60\0\0')
            def close(self):pass
        dev=Device()
        module=types.SimpleNamespace(enumerate=lambda *args:[{'path':b'device'}],device=lambda:dev)
        with patch.dict('sys.modules',{'hid':module}):
            t=HidTransport();t.open();self.assertEqual(t.exchange(r),b'\x07\x60\0\0');t.close()
            self.assertEqual(dev.sent,b'\0'+r.packet())
            module.enumerate=lambda *args:[{'path':b'a'},{'path':b'b'}]
            with self.assertRaises(ProtocolError):HidTransport().open()


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.old=b'\x55'*fw.APP_SIZE;self.new=bytes((i*13)&255 for i in range(fw.APP_SIZE))
        self.known=patch.object(fw,'KNOWN',[{'bytes':fw.APP_SIZE,'sha256':fw.sha(b),'name':n} for b,n in [(self.old,'old'),(self.new,'new')]])
        self.known.start();self.addCleanup(self.known.stop)
        self.device=Simulator(self.old)

    def installer(self,**kw):
        return Installer(self.device,self.temp.name,**kw)

    def test_install_backup_peer_preservation_and_restore(self):
        job=self.installer();directory=job.install(self.new)
        self.assertEqual((directory/'app.bin').read_bytes(),self.old)
        self.assertEqual((directory/'peer.bin').read_bytes(),self.device.peer)
        self.assertEqual(self.device.app,self.new)
        self.assertEqual(self.device.calls[-1].command,7)
        self.assertTrue(self.device.closed)
        self.assertEqual(load_backup(directory/'backup.json'),(self.old,111))
        record=json.loads((directory/'backup.json').read_text());self.assertEqual(record['status'],'complete')
        self.assertTrue(record['peer_preserved'])

    def test_unknown_preimage_never_erases(self):
        self.device.app=b'\x44'*fw.APP_SIZE
        with self.assertRaises(ProtocolError):self.installer().install(self.new)
        self.assertFalse(any(r.command in (2,3,4,7) for r in self.device.calls))

    def test_read_failure_never_erases(self):
        self.device.fail=5
        with self.assertRaises(ProtocolError):self.installer().install(self.new)
        self.assertFalse(any(r.command in (2,3,4,7) for r in self.device.calls))

    def test_write_failure_has_no_retry_or_reset(self):
        self.device.fail=3
        with self.assertRaises(ProtocolError):self.installer().install(self.new)
        self.assertEqual(sum(r.command==3 for r in self.device.calls),1)
        self.assertFalse(any(r.command==7 for r in self.device.calls))

    def test_corrupt_readback_prevents_reset(self):
        self.device.corrupt=True
        with self.assertRaises(ProtocolError):self.installer().install(self.new)
        self.assertFalse(any(r.command==7 for r in self.device.calls))

    def test_cancel_before_open(self):
        with self.assertRaises(Cancelled):self.installer(cancelled=lambda:True).install(self.new)
        self.assertEqual(self.device.calls,[])

    def test_damaged_current_image_can_restore_known_backup(self):
        self.device.app=b'\xff'*fw.APP_SIZE
        self.installer().install(self.old,recovery=True)
        self.assertEqual(self.device.app,self.old)

    def test_backup_persist_failure_never_erases(self):
        with patch('ultimate_updater.service.atomic_write',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.installer().install(self.new)
        self.assertFalse(any(r.command in (2,3,4,7) for r in self.device.calls))

    def test_unsupported_version_never_erases(self):
        self.device.version=struct.pack('<I',999)
        with self.assertRaises(ProtocolError):self.installer().install(self.new)
        self.assertFalse(any(r.command in (2,3,4,7) for r in self.device.calls))


if __name__=='__main__':unittest.main()
