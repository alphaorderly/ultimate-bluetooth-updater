"""Download pinned official inputs into ignored cache and verify assembled output."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ultimate_updater.firmware import fetch_source, compose, sha, PATCH

if __name__=='__main__':
    cache=Path('local-cache')
    result=compose(fetch_source('stock',cache,print),fetch_source('radio',cache,print))
    assert sha(result)==PATCH['target_sha256']
    print('Firmware reconstruction matches the device-tested image:',sha(result))
