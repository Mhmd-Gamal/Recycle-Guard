"""Collect installed runtime/build dependency notices for the portable distribution."""
from pathlib import Path
import importlib.metadata as metadata
import sys

root=Path(__file__).resolve().parents[1]
names=['fastapi','uvicorn','starlette','pydantic','pydantic-core','anyio','click','h11','idna','sniffio','typing-extensions','annotated-types','annotated-doc','typing-inspection','websockets','python-dotenv','watchfiles','httptools','pyyaml','opentelemetry-api','importlib-metadata','zipp','packaging','setuptools','pyinstaller','pyinstaller-hooks-contrib','altgraph','pefile','pywin32-ctypes']
parts=['RECYCLEGUARD THIRD-PARTY NOTICES\n\nThis file collects licenses/notices from installed runtime and build-tool distributions. Build tools are not necessarily included in the executable. Each dependency retains its original license. Project code has no selected redistribution license yet; a project license remains to be selected before public release.\n']
license_path=Path(sys.base_prefix)/'LICENSE.txt'
if license_path.exists():parts.append('PYTHON\n'+license_path.read_text(encoding='utf-8',errors='replace'))
for name in names:
    try: dist=metadata.distribution(name)
    except metadata.PackageNotFoundError:continue
    parts.append('\n'+'='*72+'\n'+dist.metadata['Name']+' '+dist.version+'\n')
    found=False
    for file in dist.files or []:
        lower=str(file).lower()
        if ('.dist-info/' in lower or name=='pyinstaller') and any(word in Path(str(file)).name.lower() for word in ('license','copying','notice')):
            path=Path(dist.locate_file(file))
            if path.is_file():
                parts.append(path.read_text(encoding='utf-8',errors='replace'));found=True
    if not found:parts.append('License metadata: '+str(dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'Refer to upstream distribution')+'\nHome: '+str(dist.metadata.get('Home-page','')))
(root/'docs/THIRD_PARTY_NOTICES.txt').write_text('\n\n'.join(parts),encoding='utf-8')
print('Collected dependency notices.')
