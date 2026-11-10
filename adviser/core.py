"""IPC adapter to the authoritative C# simulator (not a Python reimplementation)."""
import json
from pathlib import Path
import subprocess
import threading
import sys

ROOT = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


class Core:
    def __init__(self):
        exe = ROOT / "build" / "RecycleGuard.Core.exe"
        if not exe.exists(): raise RuntimeError("Run scripts/build-core.ps1 first")
        self.process = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.lock = threading.RLock()

    def call(self, op, **kwargs):
        with self.lock:
            if self.process.poll() is not None: raise RuntimeError("C# core exited unexpectedly")
            self.process.stdin.write(json.dumps({"op": op, **kwargs}) + "\n")
            self.process.stdin.flush()
            line = self.process.stdout.readline()
            if not line: raise RuntimeError("C# core closed output")
            result = json.loads(line)
            if "error" in result: raise ValueError(result["error"])
            return result

    def close(self):
        with self.lock:
            if self.process.poll() is None:
                self.process.stdin.close()
                try: self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            self.process.stdout.close()
            self.process.stderr.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
