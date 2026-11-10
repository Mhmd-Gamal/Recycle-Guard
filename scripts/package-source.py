"""Archive the locally committed source and evidence, without application attachments."""
from pathlib import Path
import subprocess
import zipfile
import hashlib
import json

root=Path(__file__).resolve().parents[1]
files=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode('utf-8').split('\0')
out=root/'dist/RecycleGuard-Source.zip';out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for relative in files:
        if relative:archive.write(root/relative,'RecycleGuard/'+relative)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()
manifest={'source_commit':commit,'unity_player_built':False,'real_llm_evaluated':False,'artifacts':{}}
for path in [out,root/'dist/RecycleGuard-Windows.zip',root/'output/pdf/RecycleGuard-Technical-Brief.pdf',root/'artifacts/demo/RecycleGuard-browser-demo.webm']:
    manifest['artifacts'][str(path.relative_to(root)).replace('\\','/')]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(root/'dist/RELEASE-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest,indent=2))
