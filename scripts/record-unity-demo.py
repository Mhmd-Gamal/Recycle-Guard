"""Record the Unity player's scripted walkthrough (-rgDemo) to a WebM file.

The footage is the real standalone player. The player saves its own rendered frames
(-rgCaptureDir), so nothing from the desktop is captured and nothing is composited. This
script starts the adviser service on 127.0.0.1:8765 if it is not already running, so the
recommendations in the video are live calls, then encodes the frames.

    python scripts/record-unity-demo.py --player C:/path/to/RecycleGuard.exe

Requires Pillow and an ffmpeg with VP8 (the one Playwright installs works).
"""
import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
HEALTH = "http://127.0.0.1:8765/health"
FPS = 8  # must match Time.captureFramerate in IncidentLab.Demo


def find_ffmpeg(explicit):
    if explicit: return explicit
    found = shutil.which("ffmpeg")
    if found: return found
    cache = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    for candidate in sorted(cache.glob("ffmpeg-*/ffmpeg-win64.exe"), reverse=True): return str(candidate)
    sys.exit("ffmpeg not found. Pass --ffmpeg, or run: npx playwright install ffmpeg")


def adviser_running():
    try:
        with urllib.request.urlopen(HEALTH, timeout=2) as response: return response.status == 200
    except OSError:
        return False


def start_adviser():
    if adviser_running(): return None
    service = subprocess.Popen([sys.executable, "-m", "uvicorn", "adviser.app:app", "--host", "127.0.0.1", "--port", "8765"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(40):
        if adviser_running(): return service
        time.sleep(.5)
    service.kill()
    sys.exit("The adviser service did not start. Run scripts/build-core.ps1 first.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--player", default=str(ROOT / "dist" / "UnityWindows" / "RecycleGuard.exe"))
    parser.add_argument("--output", default=str(ROOT / "artifacts" / "demo" / "RecycleGuard-unity-demo.webm"))
    parser.add_argument("--ffmpeg", default="")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--stills", default="", help="optional folder for one JPEG every 8 seconds, for review")
    args = parser.parse_args()
    if not Path(args.player).exists(): sys.exit(f"Player not found: {args.player}")
    ffmpeg = find_ffmpeg(args.ffmpeg)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    service = start_adviser()
    try:
        with tempfile.TemporaryDirectory(prefix="recycleguard-frames-") as frames_dir:
            player = subprocess.run([args.player, "-rgDemo", "-rgCaptureDir", frames_dir, "-screen-fullscreen", "0", "-screen-width", str(args.width), "-screen-height", str(args.height)], timeout=1800)
            frames = sorted(Path(frames_dir).glob("frame-*.png"))
            if not frames: sys.exit("The player saved no frames.")
            encoder = subprocess.Popen([ffmpeg, "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(FPS), "-i", "pipe:0", "-c:v", "libvpx", "-qmin", "4", "-qmax", "40", "-crf", "12", "-b:v", "1500k", "-deadline", "good", "-cpu-used", "4", "-y", args.output], stdin=subprocess.PIPE)
            written = 0
            for index, frame in enumerate(frames):
                try:
                    with Image.open(frame) as image:
                        image = image.convert("RGB")
                        image = image.crop((0, 0, image.width - image.width % 2, image.height - image.height % 2))
                        buffer = io.BytesIO()
                        image.save(buffer, "JPEG", quality=92)
                except OSError:
                    continue  # a frame still being written when the player quit
                encoder.stdin.write(buffer.getvalue())
                written += 1
                if args.stills and index % (FPS * 8) == FPS * 4:
                    Path(args.stills).mkdir(parents=True, exist_ok=True)
                    (Path(args.stills) / f"t{index // FPS:03d}.jpg").write_bytes(buffer.getvalue())
            encoder.stdin.close()
            encoder.wait(timeout=600)
    finally:
        if service: service.terminate()
    print(f"Encoded {written} frames ({written / FPS:.0f} s at {FPS} fps) to {args.output}")
    print(f"Player exit code: {player.returncode}")


if __name__ == "__main__":
    main()
