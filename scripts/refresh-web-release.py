"""Refresh only bundled web assets; retain the already tested Python/C# binaries."""
from pathlib import Path
import zipfile
import hashlib
import json

root=Path(__file__).resolve().parents[1]
release=root/'dist/RecycleGuard-Windows.zip'
updated=root/'dist/RecycleGuard-Windows.new.zip'
sources={f'RecycleGuard/_internal/web/{p.name}':p for p in (root/'web').iterdir() if p.is_file()}
with zipfile.ZipFile(release) as old, zipfile.ZipFile(updated,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as new:
    assert set(sources).issubset(set(old.namelist())), 'Unexpected portable archive structure'
    for entry in old.infolist():
        new.writestr(entry,sources[entry.filename].read_bytes() if entry.filename in sources else old.read(entry))
with zipfile.ZipFile(updated) as check:
    assert check.testzip() is None
    for name,p in sources.items(): assert check.read(name)==p.read_bytes()
updated.replace(release)
print(json.dumps({'release':str(release),'sha256':hashlib.sha256(release.read_bytes()).hexdigest(),'updated_assets':list(sources)},indent=2))
