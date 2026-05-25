"""
Generate professional terminal demo GIFs for RUMI README.
Rounded corners, black bg, shiny effects, deep colors.
Uses Pillow for frames and ffmpeg for optimization.
"""
import os, math, subprocess
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 900, 580
FONT_PATH = "C:/Windows/Fonts/consola.ttf"
FONT_PATH_BOLD = "C:/Windows/Fonts/consolab.ttf"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

FONT_SIZES = {"title": 26, "heading": 20, "body": 17, "small": 13}
fonts = {k: ImageFont.truetype(FONT_PATH, v) for k, v in FONT_SIZES.items()}
font_bold = ImageFont.truetype(FONT_PATH_BOLD, 18)

BG = (0, 0, 0)            # true black
TITLE_BG = (10, 10, 20)   # near-black title bar
TEXT = (210, 210, 220)     # soft white
GREEN = (60, 230, 140)     # vibrant green
CYAN = (50, 190, 255)      # bright cyan
YELLOW = (255, 210, 50)    # warm yellow
RED = (255, 80, 80)        # vibrant red
MUTED = (100, 100, 130)    # dim blue-gray
ORANGE = (255, 160, 50)    # RUMI brand orange
PURPLE = (160, 100, 255)   # accent
PINK = (255, 80, 180)      # accent
PROMPT = (60, 230, 140)    # green prompt

RADIUS = 16  # rounded corner radius

os.makedirs(OUT_DIR, exist_ok=True)


def rounded_rect(draw, xy, radius, fill, outline=None):
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def add_shiny_overlay(draw, x1, y1, x2, y2):
    """Add a subtle glossy highlight at the top of the terminal."""
    for i in range(20):
        alpha = int(12 * (1 - i / 20))
        draw.rectangle([x1 + 30, y1 + 35 + i, x2 - 30, y1 + 36 + i],
                       fill=(255, 255, 255, 0))


def make_terminal_frame(draw, img, lines, title="RUMI v2.0"):
    """Draw the terminal window with rounded corners and shiny effects."""
    w, h = WIDTH, HEIGHT
    margin = 20
    # Glow effect behind terminal
    for g in range(3, 0, -1):
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        gdraw.rounded_rectangle(
            (margin - g, margin - g, w - margin + g, h - margin + g),
            radius=RADIUS + g, outline=(50, 50, 80, 20 - g * 5), width=2)
        img.alpha_composite(glow)
    # Terminal body
    rounded_rect(draw, (margin, margin, w - margin, h - margin), RADIUS, fill=BG)
    # Title bar
    rounded_rect(draw, (margin, margin, w - margin, margin + 34), RADIUS,
                 fill=TITLE_BG)
    draw.rectangle([margin, margin + 20, w - margin, margin + 34], fill=TITLE_BG)
    # Window buttons
    for bx, bc in [(margin + 14, (255, 80, 80)), (margin + 34, (255, 210, 50)),
                   (margin + 54, (60, 230, 140))]:
        draw.ellipse([bx, margin + 11, bx + 12, margin + 23], fill=bc)
        # button shine
        draw.ellipse([bx + 2, margin + 13, bx + 6, margin + 17], fill=(255, 255, 255, 40))
    # Title text
    draw.text((w // 2 - 50, margin + 10), title, font=fonts["small"], fill=MUTED)
    # Shiny horizontal highlight on title bar
    draw.rectangle([margin + 60, margin + 3, w - margin - 60, margin + 4],
                   fill=(255, 255, 255, 12))
    # Content area
    y = margin + 50
    for text, color, font_key in lines:
        fnt = fonts.get(font_key, fonts["body"])
        draw.text((margin + 16, y), text, font=fnt, fill=color)
        y += 24
    # Bottom shine
    draw.rectangle([margin + 40, h - margin - 6, w - margin - 40, h - margin - 5],
                   fill=(255, 255, 255, 6))


def frame_from_lines(lines, title="RUMI v2.0"):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Subtle radial background glow
    for r in range(200, 0, -4):
        alpha = max(0, 3 - r // 80)
        c = (20, 20, 50)
        draw.ellipse([WIDTH // 2 - r, HEIGHT // 2 - r,
                      WIDTH // 2 + r, HEIGHT // 2 + r],
                     fill=(*c, alpha))
    make_terminal_frame(draw, img, lines, title)
    return img


def create_quickstart_gif():
    frames = []
    all_lines = []

    # 1: Boot screen
    lines = [
        ("[BOOT] RUMI v2.0 — Research & Unified Machine Intelligence", CYAN, "body"),
        ("[BOOT] Initializing cognitive architecture...", MUTED, "body"),
        ("[BOOT] Loading brain modules...", MUTED, "body"),
    ]
    all_lines.append(lines)

    # 2-6: Memory modules loading
    mem_modules = [
        "neural_memory", "episodic_memory", "vector_memory",
        "active_inference", "curiosity_engine"
    ]
    for i, mod in enumerate(mem_modules):
        lines = [
            ("[BOOT] RUMI v2.0 — Research & Unified Machine Intelligence", CYAN, "body"),
            ("[BOOT] Initializing cognitive architecture...", MUTED, "body"),
        ]
        for j in range(i + 1):
            c = GREEN if j < i else YELLOW
            st = "OK" if j < i else "RUNNING"
            lines.append((f"  ✓ {mem_modules[j]:30s} [{st}]", c, "body"))
        lines.append(("", None, "body"))
        lines.append((f"  [{i+1}/{len(mem_modules)}] memory modules online...", MUTED, "body"))
        all_lines.append(lines)

    # 7: All modules + scientist ready
    lines = [
        ("[BOOT] RUMI v2.0 — Research & Unified Machine Intelligence", CYAN, "body"),
        ("[BOOT] All systems nominal.", GREEN, "body"),
        ("  ✓ 9 memory systems              [ONLINE]", GREEN, "body"),
        ("  ✓ 8 reasoning modules            [ONLINE]", GREEN, "body"),
        ("  ✓ 6 planning modules             [ONLINE]", GREEN, "body"),
        ("  ✓ 15 scientist modules           [ONLINE]", GREEN, "body"),
        ("  ✓ 11 research agents             [READY]", GREEN, "body"),
        ("  ✓ 40+ tool actions               [ARMED]", GREEN, "body"),
        ("", None, "body"),
        ("  System ready. 60+ modules online.", CYAN, "body"),
        ("", None, "body"),
        ("  ───────────────────────────────────────", MUTED, "small"),
        ("  RUMI v2.0  |  Gemini 2.5 Flash  |  ~200MB RAM", MUTED, "small"),
        ("  ───────────────────────────────────────", MUTED, "small"),
    ]
    all_lines.append(lines)

    # 8: Prompt
    lines = [
        ("╔══════════════════════════════════════════════╗", ORANGE, "body"),
        ("║     🧬  RUMI  —  Ready for research          ║", ORANGE, "body"),
        ("╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ("", None, "body"),
        ("  How can I help with your research today?", TEXT, "body"),
        ("", None, "body"),
        ("  rumi > ", PROMPT, "heading"),
    ]
    all_lines.append(lines)

    # 9-14: Typing command
    cmd = 'scientist_pipeline(action="run", topic="attention mechanisms")'
    parts = ["g"] + list(cmd[1:])
    for i, ch in enumerate(parts):
        visible = cmd[:i+1]
        rest = "█" if i < len(cmd) - 1 else ""
        lines = [
            ("╔══════════════════════════════════════════════╗", ORANGE, "body"),
            ("╚══════════════════════════════════════════════╝", ORANGE, "body"),
            ("", None, "body"),
            ("  rumi > ", PROMPT, "heading"),
        ]
        # Show typed so far + cursor
        typed_text = f"  rumi > {visible}{rest}"
        lines = [
            ("╔══════════════════════════════════════════════╗", ORANGE, "body"),
            ("╚══════════════════════════════════════════════╝", ORANGE, "body"),
            ("", None, "body"),
            (typed_text, PROMPT if i < len(parts)-1 else CYAN, "heading"),
        ]
        all_lines.append(lines)

    # 15: Pipeline starts
    lines = [
        ("╔══════════════════════════════════════════════╗", ORANGE, "body"),
        ("╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ("", None, "body"),
        ("  [PIPELINE] Starting enhanced research pipeline...", CYAN, "body"),
        ("  [PIPELINE] Topic: attention mechanisms in transformers", TEXT, "body"),
        ("", None, "body"),
        ("    Phase 1/12  Literature Review       [RUNNING]  ▶", YELLOW, "body"),
        ("    Phase 2/12  Knowledge Graph         [PENDING]   ", MUTED, "body"),
        ("    Phase 3/12  Novelty Assessment      [PENDING]   ", MUTED, "body"),
        ("", None, "body"),
        ("  ═══  Searching arXiv, Semantic Scholar...  ═══", MUTED, "small"),
    ]
    all_lines.append(lines)

    # 16: Pipeline progress
    phases_done = ["Literature Review", "Knowledge Graph Retrieval",
                   "Novelty Assessment", "Hypothesis Generation",
                   "Experiment Design"]
    lines = [
        ("╔══════════════════════════════════════════════╗", ORANGE, "body"),
        ("╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ("", None, "body"),
        ("  [PIPELINE] Enhanced research pipeline — active learning", CYAN, "body"),
    ]
    for i, ph in enumerate(phases_done):
        icon, c, st = ("✅", GREEN, "DONE") if i < 4 else ("▶ ", YELLOW, "RUNNING")
        lines.append((f"    {icon}  {ph:35s} [{st}]", c, "body"))
    lines.append(("", None, "body"))
    bar = "████████████████░░░░░░░░░░░  5/12 phases"
    lines.append((f"    {bar}", YELLOW, "small"))
    all_lines.append(lines)

    # 17: Results
    lines = [
        ("╔══════════════════════════════════════════════╗", ORANGE, "body"),
        ("╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ("", None, "body"),
        ("  [PIPELINE] 12/12 phases complete — SUCCESS", GREEN, "heading"),
        ("", None, "body"),
        ("    📄  Paper:    attention_mechanisms_2026.pdf", TEXT, "body"),
        ("    📊  Data:     4 experiments, 12 charts", TEXT, "body"),
        ("    🧠  KG:       47 new entities, 128 relationships", TEXT, "body"),
        ("    🔄  Learning: 3 new strategies extracted", TEXT, "body"),
        ("    📚  BibTeX:   citation ready", TEXT, "body"),
        ("", None, "body"),
        ("  ▸  Run complete. Ready for next question.", GREEN, "body"),
        ("", None, "body"),
        ("  rumi > ", PROMPT, "heading"),
    ]
    all_lines.append(lines)

    for lines in all_lines:
        frames.append(frame_from_lines(lines))

    path = os.path.join(OUT_DIR, "rumi_demo.gif")
    durs = []
    for i in range(len(frames)):
        if i < 2: durs.append(80)
        elif i < 8: durs.append(100)
        elif i == 8: durs.append(120)
        elif i < len(frames) - 20: durs.append(30)
        elif i < len(frames) - 4: durs.append(180)
        else: durs.append(350)
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, optimize=False, disposal=1)
    print(f"Quickstart GIF: {os.path.getsize(path)} bytes")
    return path


def create_pipeline_gif():
    phases = [
        ("Literature Review", "Searching 1,247 papers across arXiv, Semantic Scholar..."),
        ("Knowledge Graph", "Extracting 89 entities, building relationship map..."),
        ("Novelty Assessment", "Comparing against prior work — computing novelty score..."),
        ("Hypothesis Generation", "GFlowNet tournament — 50 candidates, 5 generations..."),
        ("Experiment Design", "Bayesian optimal design — 3 iterations, 12 conditions..."),
        ("Experiment Execution", "Running simulations — collecting metrics..."),
        ("Analysis", "Statistical testing, effect size, visualization..."),
        ("Reproducibility", "Cross-validation, sensitivity analysis, ablation..."),
        ("Paper Generation", "Writing abstract, methods, results, discussion..."),
        ("Peer Review", "Self-review: rigor, claims, citations, limitations..."),
        ("Knowledge Update", "Merging 47 entities, 128 relationships into KG..."),
        ("Self-Improvement", "Extracting 3 learning strategies from this run..."),
    ]
    n = len(phases)
    frames = []

    # Opening
    lines = [
        ("╔══════════════════════════════════════════════╗", ORANGE, "body"),
        ("║     🔬  RUMI Scientist AI  —  12-Phase Pipeline  ║", ORANGE, "body"),
        ("╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ("", None, "body"),
        ("  Initializing research pipeline...", CYAN, "body"),
        ("  Mode: Full autonomous (active learning loop)", MUTED, "small"),
    ]
    frames.append(frame_from_lines(lines, "RUMI Scientist AI Pipeline"))

    for done in range(1, n + 1):
        lines = [
            ("╔══════════════════════════════════════════════╗", ORANGE, "body"),
            ("║     🔬  RUMI Scientist AI  —  12-Phase Pipeline  ║", ORANGE, "body"),
            ("╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ]
        for i, (name, desc) in enumerate(phases):
            if i < done:
                icon, c = "✅", GREEN
                st = "DONE"
            elif i == done:
                icon, c = "▶ ", YELLOW
                st = "RUNNING"
            else:
                icon, c = "  ", MUTED
                st = "PENDING"
            lines.append((f"  {icon}  Phase {i+1:2d}  {name:30s}  [{st}]", c, "body"))
            if i == done and done < n:
                lines.append((f"          {phases[done][1]}", MUTED, "small"))

        pct = done / n
        bw = 42
        filled = int(bw * pct)
        bar = "█" * filled + "░" * (bw - filled)
        lines.append(("", None, "body"))
        lines.append((f"  {bar}  {done}/{n} phases  ({int(pct*100)}%)", GREEN if done == n else YELLOW, "small"))
        if done == n:
            lines.append(("", None, "body"))
            lines.append(("  ✅  Pipeline complete — all modules synchronized.", GREEN, "heading"))

        frames.append(frame_from_lines(lines, "RUMI Scientist AI Pipeline"))

    durs = [200] + [180] * (n - 1) + [400]
    path = os.path.join(OUT_DIR, "rumi_pipeline.gif")
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, optimize=False, disposal=1)
    print(f"Pipeline GIF: {os.path.getsize(path)} bytes")
    return path


def create_install_gif():
    """Show installation commands being typed in a real terminal."""
    frames = []
    all_lines = []
    PS = "  PS C:\\Users\\Researcher>"
    steps = [
        "git clone https://github.com/subhansh-dev/Rumi",
        "cd rumi",
    ]
    outputs = [
        ("Cloning into 'Rumi'...", "Receiving objects: 100% (528/528), done."),
        ("", ""),
    ]

    # 1-20: Type "git clone ..." char by char
    cmd = steps[0]
    for i in range(1, len(cmd) + 1):
        typed = cmd[:i]
        cursor = "█" if i < len(cmd) else " "
        lines = [
            ("", None, "body"), ("", None, "body"), ("", None, "body"),
            ("", None, "body"),
            (f"{PS} {typed}{cursor}", GREEN, "heading"),
        ]
        all_lines.append(lines)

    # 21: show git clone output
    lines = [
        (f"{PS} {cmd}", GREEN, "heading"),
        ("", None, "body"),
        ("  Cloning into 'Rumi'...", MUTED, "body"),
        ("  Receiving objects: 100% (528/528), 1.2 MiB | 2.3 MiB/s", MUTED, "small"),
        ("  Resolving deltas: 100% (312/312), done.", MUTED, "small"),
        ("", None, "body"),
        ("  ✅  Repository cloned successfully.", GREEN, "body"),
    ]
    all_lines.append(lines)

    # 22-30: Type "cd rumi"
    cmd2 = steps[1]
    for i in range(1, len(cmd2) + 1):
        typed = cmd2[:i]
        cursor = "█" if i < len(cmd2) else " "
        lines = [
            (f"{PS} {steps[0]}", GREEN, "heading"),
            ("", None, "body"),
            ("  Cloning into 'Rumi'...", MUTED, "body"),
            ("  Receiving objects: 100% (528/528), 1.2 MiB | 2.3 MiB/s", MUTED, "small"),
            ("  Resolving deltas: 100% (312/312), done.", MUTED, "small"),
            ("", None, "body"),
            (f"{PS} {typed}{cursor}", GREEN, "heading"),
        ]
        all_lines.append(lines)

    # 31: show cd done
    lines = [
        (f"{PS} {steps[0]}", GREEN, "heading"),
        ("  Cloning into 'Rumi'...", MUTED, "body"),
        ("  Receiving objects: 100% (528/528), 1.2 MiB | 2.3 MiB/s", MUTED, "small"),
        ("  Resolving deltas: 100% (312/312), done.", MUTED, "small"),
        ("", None, "body"),
        (f"{PS} cd rumi", GREEN, "heading"),
        ("", None, "body"),
        ("  ✅  Entered project directory.", GREEN, "body"),
        ("", None, "body"),
        ("  ═══  Next: python -m venv rumi_env  ═══", MUTED, "small"),
    ]
    all_lines.append(lines)

    # 32-55: Show venv + pip install + playwright + config + launch
    step_fast = [
        ("python -m venv rumi_env", "Virtual environment created.", "✅"),
        ("rumi_env\\Scripts\\activate", "Environment activated.", "✅"),
        ("pip install -e .", "Installing 120+ dependencies... done.", "✅"),
        ("playwright install chromium", "Browser engine downloaded.", "✅"),
        ("# Edit config/api_keys.json", "Add your Gemini API key", "▶ "),
    ]
    base_history = [
        (f"{PS} {steps[0]}", GREEN, "heading"),
        ("  Cloning into 'Rumi'...", MUTED, "body"),
        ("  Receiving objects: 100% (528/528)...", MUTED, "small"),
        ("", None, "body"),
        (f"{PS} cd rumi", GREEN, "heading"),
        ("", None, "body"),
    ]
    for idx, (st_cmd, st_desc, icon) in enumerate(step_fast):
        lines = list(base_history)
        prev_done = step_fast[:idx]
        for p_cmd, p_desc, _ in prev_done:
            lines.append((f"  ✅  {p_desc}", GREEN, "body"))
        lines.append(("", None, "body"))
        lines.append((f"  {icon}  {st_cmd}", YELLOW if icon == "▶ " else GREEN, "heading"))
        lines.append(("", None, "body"))
        lines.append((f"  {st_desc}", MUTED if icon == "▶ " else GREEN, "body"))
        if icon == "▶ ":
            lines.append(("", None, "body"))
            lines.append(("  🚀  RUMI is ready! Type /personality or just start chatting.", GREEN, "heading"))
        all_lines.append(lines)

    for ls in all_lines:
        frames.append(frame_from_lines(ls))
    path = os.path.join(OUT_DIR, "rumi_install.gif")
    durs = [50]*46 + [250] + [50]*7 + [350] + [250]*5
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, optimize=False, disposal=1)
    print(f"Install GIF: {os.path.getsize(path)} bytes")
    return path


def optimize_ffmpeg(input_path):
    out = os.path.join(OUT_DIR, os.path.basename(input_path))
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "fps=12,split[s0][s1];[s0]palettegen=max_colors=64[p];[s1][p]paletteuse=dither=bayer",
        "-loop", "0", out
    ], capture_output=True)
    print(f"Optimized: {os.path.getsize(out)} bytes")


def create_intro_gif():
    """Create intro GIF: rumi command → boot → you typing haiiii :3 → reply"""
    frames = []
    all_lines = []

    USER_PROMPT = "  you > "  # clearly user input, not rumi

    # 1-4: Typing "rumi" command char by char
    cmd_word = "rumi"
    for i, ch in enumerate(cmd_word):
        typed = cmd_word[:i+1]
        cursor = "█" if i < len(cmd_word) - 1 else " "
        lines = [
            ("", None, "body"),
            ("", None, "body"),
            ("", None, "body"),
            ("", None, "body"),
            ("", None, "body"),
            ("", None, "body"),
            ("", None, "body"),
            ("", None, "body"),
            (f"  PS C:\\Users\\Researcher> {typed}{cursor}", GREEN, "heading"),
        ]
        all_lines.append(lines)

    # 5: Press Enter – boot starts
    lines = [
        ("  PS C:\\Users\\Researcher> rumi", GREEN, "heading"),
        ("", None, "body"),
        ("  ╔══════════════════════════════════════════════╗", ORANGE, "body"),
        ("  ║     🧬  RUMI v2.0  —  Initializing...        ║", ORANGE, "body"),
        ("  ╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ("", None, "body"),
        ("  [BOOT] WUMI v2.0 — Weseawch & Unified Machine Intewwigence!!", CYAN, "heading"),
        ("  [BOOT] Initiawizing cognitive awchitectuwe...", MUTED, "body"),
    ]
    all_lines.append(lines)

    # 6-10: Loading bars for modules
    load_modules = [
        "neural_memory        ████████░░░░  [42%]",
        "episodic_memory      ████████████  [88%]",
        "vectow_memowy        ██████████░░  [71%]",
        "active_infewence     ████████████  [95%]",
        "cuwiosity_engine     ████████████  [100%]",
    ]
    for i, mod in enumerate(load_modules):
        lines = [
            ("  ╔══════════════════════════════════════════════╗", ORANGE, "body"),
            ("  ║     🧬  WUMI v2.0  —  Loading brain modules  ║", ORANGE, "body"),
            ("  ╚══════════════════════════════════════════════╝", ORANGE, "body"),
            ("", None, "body"),
            ("  [BOOT] WUMI v2.0 — Weseawch & Unified Machine Intewwigence!!", CYAN, "heading"),
        ]
        for j in range(i + 1):
            completed = j < i
            c = GREEN if completed else YELLOW
            icon = "✅" if completed else "⏳"
            lines.append((f"  {icon}  {load_modules[j]}", c, "small"))
        lines.append(("", None, "body"))
        lines.append((f"  [{i+1}/{len(load_modules)}] modules woaded...", MUTED, "body"))
        all_lines.append(lines)

    # 11: Systems online
    lines = [
        ("  ╔══════════════════════════════════════════════╗", ORANGE, "body"),
        ("  ║     🧬  WUMI v2.0  —  Online!!               ║", ORANGE, "body"),
        ("  ╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ("", None, "body"),
        ("  [BOOT] Aww systems nominaw!!", GREEN, "heading"),
        ("  ✅  60+ bwain modules               [ONWINE]", GREEN, "body"),
        ("  ✅  15 scientist moduwes           [ONWINE]", GREEN, "body"),
        ("  ✅  11 weseawch agents              [WEADY]", GREEN, "body"),
        ("", None, "body"),
        ("  System weady!! hewwo!! ^_^", CYAN, "heading"),
        ("", None, "body"),
        ("  ───────────────────────────────────────", MUTED, "small"),
        ("  WUMI v2.0  |  Gemini 2.5 Fwash  |  ~200MB WAM", MUTED, "small"),
        ("  ───────────────────────────────────────", MUTED, "small"),
    ]
    all_lines.append(lines)

    # 12: Prompt shows — WUMI says hewwo, user prompt empty
    lines = [
        ("  ╔══════════════════════════════════════════════╗", ORANGE, "body"),
        ("  ║     🧬  WUMI  —  Hewwo!!                     ║", ORANGE, "body"),
        ("  ╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ("", None, "body"),
        ("  Hewwo boss!! 🥺 what can i hewp you with~?", CYAN, "body"),
        ("", None, "body"),
        (f"  {USER_PROMPT}", PROMPT, "heading"),
    ]
    all_lines.append(lines)

    # 13-22: Typing "haiiiii :3" char by char at USER prompt
    msg = "haiiiii :3"
    for i, ch in enumerate(msg):
        typed = msg[:i+1]
        cursor = "█" if i < len(msg) - 1 else " "
        lines = [
            ("  ╔══════════════════════════════════════════════╗", ORANGE, "body"),
            ("  ╚══════════════════════════════════════════════╝", ORANGE, "body"),
            ("", None, "body"),
            ("  Hewwo boss!! 🥺 what can i hewp you with~?", CYAN, "body"),
            ("", None, "body"),
            (f"  {USER_PROMPT}{typed}{cursor}", PINK, "heading"),
        ]
        all_lines.append(lines)

    # 23: RUMI thinks / loading indicator
    lines = [
        ("  ╔══════════════════════════════════════════════╗", ORANGE, "body"),
        ("  ╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ("", None, "body"),
        ("  Hewwo boss!! 🥺 what can i hewp you with~?", CYAN, "body"),
        ("", None, "body"),
        (f"  {USER_PROMPT}haiiiii :3", PINK, "heading"),
        ("", None, "body"),
        ("  ⏳ WUMI is pwocessing...", YELLOW, "body"),
        ("  ✨  synthesizing wovingly...", YELLOW, "small"),
    ]
    all_lines.append(lines)

    # 24: RUMI responds with cute uwu reply (LONG LAST FRAME)
    lines = [
        ("  ╔══════════════════════════════════════════════╗", ORANGE, "body"),
        ("  ╚══════════════════════════════════════════════╝", ORANGE, "body"),
        ("", None, "body"),
        ("  Hewwo boss!! 🥺 what can i hewp you with~?", CYAN, "body"),
        ("", None, "body"),
        (f"  {USER_PROMPT}haiiiii :3", PINK, "heading"),
        ("", None, "body"),
        ("  hewwooo!!! 🧪✨", CYAN, "heading"),
        ("", None, "body"),
        ("  how can i hewp wiff youw", CYAN, "body"),
        ("  science today~? 🔬", CYAN, "body"),
        ("", None, "body"),
        ("  i can do wesearch, wite code,", CYAN, "body"),
        ("  ow just chat!! tell me evewything!!", CYAN, "body"),
        ("", None, "body"),
        ("  🐣  uwu  |  weady to serve boss  |  💖", MUTED, "small"),
    ]
    all_lines.append(lines)

    for ls in all_lines:
        frames.append(frame_from_lines(ls))
    path = os.path.join(OUT_DIR, "rumi_intro.gif")
    durs = [250]*4 + [400] + [150]*5 + [350] + [200] + [120]*10 + [250] + [4000]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, optimize=False, disposal=1)
    print(f"Intro GIF: {os.path.getsize(path)} bytes")
    return path


if __name__ == "__main__":
    g_intro = create_intro_gif()
    g1 = create_quickstart_gif()
    g2 = create_pipeline_gif()
    g3 = create_install_gif()
    # opt with ffmpeg disabled - causes rendering issues on some viewers
    # for g in [g_intro, g1, g2, g3]:
    #     optimize_ffmpeg(g)
