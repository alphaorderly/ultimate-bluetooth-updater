"""Build the pinned firmware locally; never distribute vendor firmware bytes."""
from pathlib import Path
import hashlib
import json
import os
import struct
import urllib.request

RESOURCES = Path(__file__).with_name('resources')
PATCH = json.loads((RESOURCES / 'patch.json').read_text())
SEEDS = json.loads((RESOURCES / 'seeds.json').read_text())
KNOWN = json.loads((RESOURCES / 'known-images.json').read_text())
APP_BASE, VERSION_ADDRESS, PEER_BASE = 0x01018000, 0x01017040, 0x0107e000
APP_SIZE = PATCH['target_size']
SOURCES = {
    'stock': {
        'sha256': '1030145fec364aceb55ceaed221396131dcf02eaaeeb8bd9ad4044ba5596074d',
        'size': 104988,
        'urls': [
            'http://beta.8bitdo.com:8080/firmwareFile/upload/e5d922bb-e461-4c67-9482-4762876705f0.dat',
            'http://dl.8bitdo.com:8080/firmwareFile/upload/78db64eb-7005-4220-927e-19424aff8fd7.dat',
        ],
    },
    'radio': {
        'sha256': 'bf9f4f56a16ca4adc74a07855781612383e3c77ed62ba3717154829c41ef9193',
        'size': 142392,
        'urls': [
            'http://beta.8bitdo.com:8080/firmwareFile/upload/3c59e562-0c34-47c6-a52b-c0129f032315.dat',
            'http://dl.8bitdo.com:8080/firmwareFile/upload/bfe54205-6aae-4e9b-bd70-4e406a525133.dat',
        ],
    },
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def ror(value, count):
    count %= 32
    return ((value >> count) | (value << ((32-count) % 32))) & 0xffffffff


def transform(data, encrypt=False):
    # YiChip schedule from AeroModes/8CryptDo (MIT); see THIRD_PARTY.md.
    if len(data) % 4:
        raise ValueError('Firmware must contain complete 32-bit words')
    indices = ((0, 0x82, 0x83, 0x81, 3, 0x81, 0x83, 0x81),
               (0x86, 0x83, 0x81, 0x82, 3, 5, 0x82, 0x82))
    words = struct.unpack(f'<{len(data)//4}I', data)
    out = []
    for i, word in enumerate(words):
        block, position = divmod(i, 128)
        e = (block + (block >> 8)) & 255
        other = e ^ 0xf9
        hi, lo = e ^ indices[e >> 7][e & 7], other ^ indices[other >> 7][other & 7]
        counter = (block*0x01200210 + (block >> 8) + position*0xee97fafa) & 0xffffffff
        key = counter ^ ror((SEEDS[hi] << 16) | SEEDS[lo], 16*position)
        previous = (out[-1] if encrypt else words[i-1]) if position else 0
        out.append(word ^ key ^ (ror(previous, 18) if position else 0))
    return struct.pack(f'<{len(out)}I', *out)


def validate_source(kind, data):
    spec = SOURCES[kind]
    if len(data) != spec['size'] or sha(data) != spec['sha256']:
        raise ValueError(f'{kind}: official firmware hash mismatch; file rejected')
    return data


def fetch_source(kind, cache, status=lambda _: None):
    cache = Path(cache)
    path = cache / (kind + '.dat')
    if path.exists():
        try:
            return validate_source(kind, path.read_bytes())
        except ValueError:
            pass
    errors = []
    for url in SOURCES[kind]['urls']:
        try:
            status(f'공식 펌웨어 다운로드 · {kind}')
            request = urllib.request.Request(url, headers={'User-Agent': 'UltimateBluetoothUpdater/1.0'})
            with urllib.request.urlopen(request, timeout=20) as response:
                data = response.read(SOURCES[kind]['size'] + 1)
            validate_source(kind, data)
            atomic_write(path, data)
            return data
        except (OSError, ValueError) as error:
            errors.append(str(error))
    raise RuntimeError('공식 파일 다운로드 실패. ‘공식 파일 가져오기’로 파일을 선택할 수 있습니다.\n' + '\n'.join(errors))


def import_source(path, cache):
    data = Path(path).read_bytes()
    for kind in SOURCES:
        if sha(data) == SOURCES[kind]['sha256']:
            validate_source(kind, data)
            atomic_write(Path(cache) / (kind+'.dat'), data)
            return kind
    raise ValueError('지원하는 공식 Ultimate 1.11 / Ultimate 2 v2.00 파일이 아닙니다.')


def compose(stock, donor):
    validate_source('stock', stock)
    validate_source('radio', donor)
    app = bytearray(transform(stock[28:]))
    if sha(app) != PATCH['base_sha256']:
        raise ValueError('Unexpected base firmware')
    donor_app = transform(donor[8760:])
    radio = donor_app[115752:115752+7974]
    if sha(radio) != PATCH['radio_sha256']:
        raise ValueError('Unexpected radio firmware')
    for patch in PATCH['patches']:
        offset = patch['offset']
        before, after = bytes.fromhex(patch['before']), bytes.fromhex(patch['after'])
        if app[offset:offset+len(before)] != before or len(before) != len(after):
            raise ValueError('Patch precondition mismatch')
        app[offset:offset+len(after)] = after
    app.extend(b'\xff' * (APP_SIZE-len(app)))
    code = bytes.fromhex(PATCH['append_hex'])
    app[PATCH['append_offset']:PATCH['append_offset']+len(code)] = code
    app[PATCH['radio_offset']:PATCH['radio_offset']+len(radio)] = radio
    if len(app) != APP_SIZE or sha(app) != PATCH['target_sha256']:
        raise ValueError('Generated firmware does not match the tested release')
    return bytes(app)


def identify_image(data):
    for image in KNOWN:
        n = image['bytes']
        if len(data) >= n and sha(data[:n]) == image['sha256'] and all(b == 255 for b in data[n:]):
            return image['name']
    return None
