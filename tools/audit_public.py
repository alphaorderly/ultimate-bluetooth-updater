"""Release boundary: no vendor firmware, device dumps, local paths or credentials."""
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files'],cwd=root,text=True).splitlines()
errors=[]
for name in paths:
    p=root/name
    if p.suffix.lower() in ('.dat','.bin','.elf','.dmp') or any(part in ('backups','runs','local-cache','.venv') for part in p.relative_to(root).parts):
        errors.append(name)
    if p.suffix in ('.py','.md','.json','.yml','.txt','.c','.h','.S'):
        text=p.read_text(errors='replace')
        # Construct patterns to avoid matching the audit script itself.
        for pattern in ['/Users/'+'woo/', 'gh'+'p_', 'gh'+'o_', 'github_'+'pat_']:
            if pattern in text:errors.append(name+': local path or token pattern')
if errors:raise SystemExit('\n'.join(errors))
print(f'Public-tree audit passed: {len(paths)} tracked files; no firmware/dumps/tokens.')
