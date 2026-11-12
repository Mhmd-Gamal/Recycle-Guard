"""Real mouse clicks against the built Unity player (not collected by pytest).

The -rgSmoke and -rgDemo modes call the client's methods directly. This script instead sends
operating-system clicks to the player window, so it exercises IMGUI hit-testing, the scaled
layout and the 3D zone raycast. It saves a picture of the window's client area after each
stage for a person to inspect; it does not judge the pictures itself.

    python tests/unity_clicks.py --player C:/path/to/RecycleGuard.exe --out C:/path/to/folder

It moves the real mouse for about 20 seconds and clicks only while the player window is in
front and under the cursor. Run it with the adviser service stopped: one stage checks the
"adviser unavailable" message. Windows only.
"""
import argparse
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import ImageGrab

user32 = ctypes.windll.user32
user32.WindowFromPoint.restype = wintypes.HWND
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]

# Targets in the client's 1600 x 900 layout units (see IncidentLab.OnGUI).
DELAYED, NEW_INCIDENT = (1386, 53), (1137, 135)
SORTING_HALL_3D, LOADING_YARD_CARD = (770, 337), (128, 632)
INSPECT, EVACUATE, WAIT = (118, 775), (316, 775), (910, 775)
REQUEST_ADVICE = (1315, 328)


def window_of(pid):
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd): found.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    return found[0] if found else None


def client_rect(hwnd):
    rect, origin = wintypes.RECT(), wintypes.POINT(0, 0)
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    return origin.x, origin.y, rect.right, rect.bottom


def click(hwnd, target):
    left, top, width, height = client_rect(hwnd)
    x, y = left + round(target[0] * width / 1600), top + round(target[1] * height / 900)
    under = user32.GetAncestor(user32.WindowFromPoint(wintypes.POINT(x, y)), 2)
    if user32.GetForegroundWindow() != hwnd or under != hwnd:
        sys.exit("The player window is not in front; stopped without clicking.")
    user32.SetCursorPos(x, y)
    time.sleep(.15)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(.06)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(.7)


def picture(hwnd, folder, name):
    left, top, width, height = client_rect(hwnd)
    ImageGrab.grab(bbox=(left, top, left + width, top + height)).save(Path(folder) / f"{name}.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--player", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    Path(args.out).mkdir(parents=True, exist_ok=True)
    user32.SetProcessDPIAware()
    start = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(start))
    player = subprocess.Popen([args.player, "-rgScenario", "reliable", "-rgSeed", "7", "-screen-fullscreen", "0", "-screen-width", "1152", "-screen-height", "648"])
    try:
        hwnd = None
        for _ in range(120):
            hwnd = window_of(player.pid)
            if hwnd: break
            time.sleep(.25)
        if not hwnd: sys.exit("The player window did not appear.")
        time.sleep(6)  # splash screen
        user32.SetForegroundWindow(hwnd)
        time.sleep(.5)
        picture(hwnd, args.out, "1-start-reliable-seed-7")
        click(hwnd, DELAYED)
        picture(hwnd, args.out, "2-delayed-selected-pending")
        click(hwnd, NEW_INCIDENT)
        click(hwnd, SORTING_HALL_3D)
        picture(hwnd, args.out, "3-new-incident-zone-picked-in-3d")
        click(hwnd, LOADING_YARD_CARD)
        for _ in range(3): click(hwnd, WAIT)
        picture(hwnd, args.out, "4-card-picked-three-waits")
        click(hwnd, EVACUATE)
        picture(hwnd, args.out, "5-evacuate-on-stale-evidence")
        click(hwnd, REQUEST_ADVICE)
        time.sleep(5)
        picture(hwnd, args.out, "6-adviser-offline")
        click(hwnd, INSPECT)
        picture(hwnd, args.out, "7-inspect")
    finally:
        player.terminate()
        user32.SetCursorPos(start.x, start.y)
    print(f"Saved 7 pictures to {args.out}")


if __name__ == "__main__":
    main()
