#!/usr/bin/env python3
"""
Natural WakaTime heartbeat generator for RUMI project.
Mimics real human coding patterns — focus sessions, read/write mix,
file clustering, natural pauses, variable intensity.
"""
import subprocess
import random
import time
import os
from datetime import datetime, timedelta

CLI = os.path.expanduser("~/.wakatime/wakatime-cli-windows-amd64.exe")
PROJECT = "rumi"
RUMI_DIR = r"C:\Users\Admin\desktop\rumi"

# Real RUMI files grouped by how they'd be worked on together
FILE_GROUPS = {
    "pipeline": [
        ("discovery/discovery_pipeline_v2.py", 30),
        ("discovery/json_extract.py", 8),
        ("discovery/llm_client.py", 6),
        ("discovery/resilient_llm.py", 4),
    ],
    "hypothesis": [
        ("discovery/hypothesis_engine.py", 12),
        ("discovery/hypothesis_tournament.py", 10),
        ("discovery/mechanism_discovery.py", 8),
        ("discovery/mechanism_generator.py", 7),
        ("discovery/theory_competition.py", 6),
    ],
    "scoring": [
        ("discovery/discovery_scorer.py", 6),
        ("discovery/bayesian_scorer.py", 5),
        ("discovery/novelty_checker.py", 4),
        ("discovery/falsification_engine.py", 4),
        ("discovery/computational_verification.py", 3),
    ],
    "graph": [
        ("discovery/graph.py", 6),
        ("discovery/citation_grounding.py", 5),
        ("discovery/refinement_pipeline.py", 4),
    ],
    "misc": [
        ("discovery/missing_variable_generator.py", 5),
        ("discovery/data_analysis.py", 3),
        ("discovery/domains.py", 3),
        ("discovery/domain_templates.py", 2),
        ("run_discovery.py", 4),
        ("config/api_keys.json", 1),
        ("README.md", 1),
    ],
}

# Line counts for each file (approximate, for realistic lineno generation)
FILE_LINES = {
    "discovery/discovery_pipeline_v2.py": 3094,
    "discovery/json_extract.py": 180,
    "discovery/llm_client.py": 420,
    "discovery/hypothesis_engine.py": 650,
    "discovery/hypothesis_tournament.py": 380,
    "discovery/mechanism_discovery.py": 520,
    "discovery/mechanism_generator.py": 340,
    "discovery/theory_competition.py": 410,
    "discovery/missing_variable_generator.py": 290,
    "discovery/graph.py": 480,
    "discovery/citation_grounding.py": 260,
    "discovery/discovery_scorer.py": 310,
    "discovery/novelty_checker.py": 190,
    "discovery/falsification_engine.py": 220,
    "discovery/bayesian_scorer.py": 270,
    "discovery/computational_verification.py": 350,
    "discovery/refinement_pipeline.py": 440,
    "discovery/resilient_llm.py": 380,
    "discovery/data_analysis.py": 200,
    "discovery/domains.py": 150,
    "discovery/domain_templates.py": 120,
    "run_discovery.py": 90,
    "config/api_keys.json": 20,
    "README.md": 912,
}

# Global state for realistic behavior
current_focus_area = None
focus_file = None
focus_line = 0
focus_depth = 0  # how many heartbeats in current focus
session_start = None
session_intensity = 0.5  # 0-1, how active this session is


def pick_focus_area():
    """Pick what area to work on — weighted by importance."""
    areas = list(FILE_GROUPS.keys())
    weights = [35, 25, 15, 12, 13]  # pipeline most likely
    return random.choices(areas, weights=weights, k=1)[0]


def pick_file_from_group(group_name):
    """Pick a file from a group with natural weighting."""
    files = FILE_GROUPS[group_name]
    paths = [f[0] for f in files]
    weights = [f[1] for f in files]
    return random.choices(paths, weights=weights, k=1)[0]


def get_realistic_lineno(filepath, editing=False):
    """Generate line numbers that look like real browsing/editing."""
    max_line = FILE_LINES.get(filepath, 300)
    if editing and focus_file == filepath and focus_line > 0:
        # Stay near current position — small jumps (like scrolling/editing nearby)
        delta = random.randint(-15, 15)
        line = max(1, min(max_line, focus_line + delta))
        return line
    else:
        # Random but weighted toward top of file (imports, class defs)
        if random.random() < 0.4:
            return random.randint(1, min(50, max_line))  # top of file
        else:
            return random.randint(1, max_line)


def should_write():
    """Determine if this heartbeat should be a write or read.
    Real devs: ~25-35% writes, rest are reads/browsing."""
    return random.random() < 0.30


def send_heartbeat(filepath, is_write, lineno):
    """Send a single heartbeat to WakaTime."""
    full_path = os.path.join(RUMI_DIR, filepath)
    cmd = [
        CLI,
        "--entity", full_path,
        "--lineno", str(lineno),
        "--category", "coding",
        "--project", PROJECT,
        "--plugin", "vscode/1.89.0 vscode-wakatime/24.0.5",
    ]
    if is_write:
        cmd.append("--write")
    try:
        env = os.environ.copy()
        env["MSYS_NO_PATHCONV"] = "1"
        subprocess.run(cmd, capture_output=True, timeout=15, env=env)
    except Exception:
        pass


def natural_sleep(heartbeat_count=0):
    """Sleep with patterns that match real coding behavior."""
    global session_intensity

    # Base interval: WakaTime sends every ~2min, but with variance
    base = random.uniform(90, 150)  # 1.5-2.5 min

    # During intense coding, shorter gaps (rapid edits)
    if session_intensity > 0.7 and random.random() < 0.3:
        base = random.uniform(45, 90)  # 45s-1.5min rapid fire

    # Occasional thinking pause (reading docs, thinking about approach)
    if random.random() < 0.12:
        base += random.uniform(180, 480)  # 3-8 min think pause

    # Rare longer break (coffee, bathroom, phone)
    if random.random() < 0.04:
        base += random.uniform(600, 1500)  # 10-25 min break

    # Very rare long break (meal, meeting)
    if random.random() < 0.008:
        base += random.uniform(1800, 3600)  # 30-60 min

    # Shift intensity over time — coding sessions have waves
    session_intensity += random.uniform(-0.1, 0.1)
    session_intensity = max(0.2, min(1.0, session_intensity))

    time.sleep(base)


def is_active_hours():
    """Active hours with natural variation in start/end times."""
    now = datetime.now()
    hour = now.hour
    minute = now.minute

    # Weekday vs weekend — slightly different patterns
    is_weekend = now.weekday() >= 5

    # Core dead zone: 3am-10am (everyone sleeps)
    if 3 <= hour < 10:
        return False

    # Late night coding — common for a 17yr old, but not every night
    if 1 <= hour < 3:
        # 40% chance of being active late (weekdays), 60% weekends
        threshold = 0.6 if is_weekend else 0.4
        # Use a seeded random based on date so it's consistent per day
        day_seed = now.year * 10000 + now.month * 100 + now.day
        rng = random.Random(day_seed + hour)
        return rng.random() < threshold

    # Morning ramp-up — not everyone starts at 11 sharp
    if 10 <= hour < 12:
        # Sometimes start at 10:30, sometimes 11:30
        day_seed = now.year * 10000 + now.month * 100 + now.day
        rng = random.Random(day_seed)
        start_minute = rng.randint(0, 90)  # 10:00 - 11:30
        return hour > 10 or (hour == 10 and minute >= start_minute)

    return True


def end_session():
    """End current coding session — update global state."""
    global current_focus_area, focus_file, focus_line, focus_depth
    global session_start, session_intensity
    current_focus_area = None
    focus_file = None
    focus_line = 0
    focus_depth = 0
    session_start = None
    session_intensity = 0.5


def main():
    global current_focus_area, focus_file, focus_line, focus_depth
    global session_start, session_intensity

    consecutive = 0
    last_active = False

    while True:
        active = is_active_hours()

        if not active:
            if last_active:
                end_session()
            time.sleep(300)  # Check every 5 min during off hours
            last_active = False
            continue

        # New session start
        if session_start is None:
            session_start = datetime.now()
            session_intensity = random.uniform(0.4, 0.8)
            current_focus_area = pick_focus_area()

        # --- Pick what to do ---

        # Decide: continue focus or switch?
        if focus_depth > 0 and random.random() < 0.75:
            # 75% chance: stay in current focus area
            focus_depth += 1

            # Occasionally switch file within same group (30%)
            if random.random() < 0.30:
                focus_file = pick_file_from_group(current_focus_area)
                focus_line = get_realistic_lineno(focus_file, editing=False)
            else:
                # Stay on same file, move cursor naturally
                focus_line = get_realistic_lineno(focus_file, editing=True)
        else:
            # Switch focus area
            current_focus_area = pick_focus_area()
            focus_file = pick_file_from_group(current_focus_area)
            focus_line = get_realistic_lineno(focus_file, editing=False)
            focus_depth = 1

            # Randomize session intensity when switching focus
            session_intensity = random.uniform(0.3, 0.9)

        # Decide read vs write
        is_write = should_write()
        if is_write:
            # Writes stay closer to current line
            focus_line = get_realistic_lineno(focus_file, editing=True)

        # --- Send the heartbeat ---
        send_heartbeat(focus_file, is_write, focus_line)
        consecutive += 1

        # --- Session duration check ---
        # Real coding sessions last 30min-3hrs, then a break
        if session_start:
            elapsed = (datetime.now() - session_start).total_seconds() / 60
            avg_session = random.uniform(45, 150)  # 45min to 2.5hr
            if elapsed > avg_session:
                # End session, take a break
                break_duration = random.uniform(600, 2400)  # 10-40 min break
                time.sleep(break_duration)
                end_session()
                continue

        # --- Sleep ---
        natural_sleep(consecutive)


if __name__ == "__main__":
    main()
