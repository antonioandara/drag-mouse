"""
drag_mouse.py
One continuous drag: mouse goes down at the start point, moves through all
segments, and releases at the end.

INPUT FILE (motions.txt by default)
-----------------------------------
- Blank lines and lines starting with '#' are ignored.
- Drag line:
    x1,y1 -> x2,y2[,duration_seconds]
- Pause line:
    SLEEP seconds

EXAMPLE
-------
-660,663 -> -961,494,1.0
SLEEP 0.1
-961,494 -> -1260,494,1.0

USAGE
-----
  pip install pyautogui
  python drag_mouse.py --file motions.txt --start-delay 4 --default-duration 1.5

NOTES
-----
- FAILSAFE: fling the mouse to ANY screen corner to abort.
"""

import argparse, time, sys, re
from typing import List, Tuple, Optional

try:
    import pyautogui
except Exception as e:
    print("ERROR: PyAutoGUI is not installed or failed to import.")
    print("Install with:  pip install pyautogui")
    print("Details:", e)
    sys.exit(1)

pyautogui.FAILSAFE = True  # move to a screen corner to abort

# x1,y1,x2,y2,duration
Drag = Tuple[int, int, int, int, Optional[float]]

drag_line_re = re.compile(
    r'^\s*(-?\d+)\s*,\s*(-?\d+)\s*->\s*(-?\d+)\s*,\s*(-?\d+)(?:\s*,\s*([0-9]*\.?[0-9]+))?\s*$'
)

def parse_file(path: str) -> List[Tuple[str, object]]:
    """
    Returns a list of steps: ("DRAG",(x1,y1,x2,y2,dur|None)) or ("SLEEP", seconds)
    """
    steps: List[Tuple[str, object]] = []
    with open(path, 'r', encoding='utf-8') as f:
        for idx, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.upper().startswith("SLEEP"):
                parts = line.split()
                if len(parts) != 2:
                    raise ValueError(f"{path}:{idx}: SLEEP requires one numeric value (seconds). Got: {line}")
                try:
                    seconds = float(parts[1])
                except ValueError:
                    raise ValueError(f"{path}:{idx}: Invalid SLEEP seconds: {parts[1]}")
                steps.append(("SLEEP", seconds))
                continue
            m = drag_line_re.match(line)
            if not m:
                raise ValueError(f"{path}:{idx}: Invalid line. Expected 'x1,y1 -> x2,y2[,duration]'. Got: {line}")
            x1, y1, x2, y2 = map(int, m.groups()[:4])
            dur_str = m.group(5)
            dur = float(dur_str) if dur_str is not None else None
            steps.append(("DRAG", (x1, y1, x2, y2, dur)))
    return steps

def run_single_hold(steps: List[Tuple[str, object]], default_duration: float, button: str, between_delay: float):
    # Find the first DRAG step to get initial press-down point
    first_drag = next((p for (k, p) in steps if k == "DRAG"), None)
    if first_drag is None:
        print("No DRAG steps found in file.")
        return
    x1, y1, _, _, _ = first_drag  # start of the first drag

    btn = button.lower()
    if btn not in ("left", "right", "middle"):
        btn = "left"

    print(f"Moving to START {x1},{y1} and pressing {btn} button.")
    pyautogui.moveTo(x1, y1)
    pyautogui.mouseDown(button=btn)

    try:
        current_x, current_y = x1, y1
        seg_index = 0
        for kind, payload in steps:
            if kind == "SLEEP":
                seconds = float(payload)
                print(f"[SLEEP] {seconds}s (holding mouse down)")
                time.sleep(seconds)
                continue

            # DRAG segment
            sx, sy, ex, ey, dur = payload
            duration = float(dur) if dur is not None else default_duration
            # If the segment start doesn't match current position, we still move there WHILE holding down.
            if (sx, sy) != (current_x, current_y):
                print(f"[WARN] Segment start {sx},{sy} != current position {current_x},{current_y}. "
                      f"Will draw a connector.")
                pyautogui.moveTo(sx, sy, duration=0)  # instantaneous reposition (still drawing)

            seg_index += 1
            print(f"[{seg_index}] MOVE while holding: {sx},{sy} -> {ex},{ey}  (duration={duration}s)")
            # Use moveTo (NOT dragTo) because we're already holding the button down.
            pyautogui.moveTo(ex, ey, duration=duration, tween=pyautogui.easeInOutQuad)
            current_x, current_y = ex, ey

            if between_delay > 0:
                time.sleep(between_delay)
    finally:
        print("Releasing mouse button.")
        pyautogui.mouseUp(button=btn)

def main():
    ap = argparse.ArgumentParser(description="One continuous mouse drag from a text file of coordinates.")
    ap.add_argument("--file", default="motions.txt", help="Path to the motions file (default: motions.txt)")
    ap.add_argument("--default-duration", type=float, default=1.5, help="Default per-segment duration (seconds) when not specified")
    ap.add_argument("--button", choices=["left", "right", "middle"], default="left", help="Mouse button to hold during the whole drag")
    ap.add_argument("--start-delay", type=float, default=2.0, help="Seconds to wait before starting")
    ap.add_argument("--between-delay", type=float, default=0.0, help="Pause between segments (seconds) while holding the button")
    args = ap.parse_args()

    print("=== drag mouse ===")
    print("Fling the mouse to ANY screen corner to abort (PyAutoGUI FAILSAFE).")
    print(f"Reading steps from: {args.file}")
    try:
        steps = parse_file(args.file)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

    print(f"Loaded {len(steps)} step(s). Starting in {args.start_delay} seconds...")
    time.sleep(args.start_delay)

    try:
        run_single_hold(steps, args.default_duration, args.button, args.between_delay)
        print("Done.")
    except pyautogui.FailSafeException:
        print("Aborted by moving mouse to a screen corner (FAILSAFE).")
    except KeyboardInterrupt:
        print("Aborted by user (Ctrl+C).")

if __name__ == "__main__":
    main()
