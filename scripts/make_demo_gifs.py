"""
Generate professional terminal demo GIFs for RUMI README.
Uses Pillow for frame generation and ffmpeg for GIF optimization.
"""
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

# ── Config ──────────────────────────────────────────────────────────
WIDTH, HEIGHT = 900, 580
FONT_PATH = "C:/Windows/Fonts/consola.ttf"
FONT_SIZE = 18
BG = (18, 18, 28)        # dark terminal bg
TEXT = (200, 200, 200)    # light gray text
GREEN = (80, 220, 120)    # success/ready
CYAN = (80, 180, 240)     # commands
YELLOW = (240, 210, 80)   # warnings/loading
RED = (240, 100, 100)     # errors
MUTED = (120, 120, 140)   # dim text
BLUE = (100, 140, 255)    # phase labels
ORANGE = (255, 170, 60)   # RUMI brand
PROMPT_COLOR = (80, 220, 120)  # green prompt

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
os.makedirs(OUT_DIR, exist_ok=True)

font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
font_small = ImageFont.truetype(FONT_PATH, 14)
font_big = ImageFont.truetype(FONT_PATH, 28)
font_title = ImageFont.truetype(FONT_PATH, 22)


def make_frame(draw, lines, cursor_line=None, cursor_pos=None):
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=BG)
    # Terminal title bar
    draw.rectangle([0, 0, WIDTH, 30], fill=(30, 30, 45))
    draw.ellipse([10, 10, 20, 20], fill=(240, 100, 100))
    draw.ellipse([26, 10, 36, 20], fill=(240, 210, 80))
    draw.ellipse([42, 10, 52, 20], fill=(80, 220, 120))
    draw.text((WIDTH // 2 - 40, 6), "RUMI  v2.0", font=font_small, fill=MUTED)
    # Content
    y = 44
    for i, (text, color) in enumerate(lines):
        draw.text((20, y), text, font=font, fill=color)
        y += 26
    # Cursor
    if cursor_line is not None:
        cy = 44 + cursor_line * 26
        cx = 20 + (cursor_pos or 0) * 10
        draw.rectangle([cx, cy, cx + 10, cy + 20], fill=TEXT)
    return y


def create_quickstart_gif():
    frames = []
    lines_list = []

    # Frame 1: Terminal boot
    lines = [
        ("[BOOT] RUMI v2.0 — Research & Unified Machine Intelligence", CYAN),
        ("[BOOT] Initializing cognitive architecture...", MUTED),
    ]
    lines_list.append(list(lines))

    # Frame 2-5: Modules loading
    modules = [
        ("neural_memory", "OK"),
        ("episodic_memory", "OK"),
        ("vector_memory", "OK"),
        ("active_inference", "OK"),
        ("causal_reasoner", "OK"),
        ("analogy_engine", "OK"),
        ("curiosity", "OK"),
        ("creativity_engine", "OK"),
    ]
    for i in range(1, len(modules) + 1):
        lines = [
            ("[BOOT] RUMI v2.0 — Research & Unified Machine Intelligence", CYAN),
            ("[BOOT] Initializing cognitive architecture...", MUTED),
        ]
        for name, status in modules[:i]:
            color = GREEN if status == "OK" else MUTED
            lines.append((f"  ✓ {name:30s} [{status}]", color))
        lines.append(("", MUTED))
        lines.append((f"  [{i}/{len(modules)}] modules online...", MUTED))
        lines_list.append(list(lines))

    # Frame 6: All modules loaded + scientist modules
    lines = [
        ("[BOOT] RUMI v2.0 — Research & Unified Machine Intelligence", CYAN),
        ("[BOOT] Initializing cognitive architecture...", MUTED),
    ]
    for name, status in modules:
        lines.append((f"  ✓ {name:30s} [{status}]", GREEN))
    lines.append(("  ✓ discovery_engine       [ONLINE]", GREEN))
    lines.append(("  ✓ novelty_checker        [ONLINE]", GREEN))
    lines.append(("  ✓ experiment_designer    [ONLINE]", GREEN))
    lines.append(("  ✓ paper_generator        [ONLINE]", GREEN))
    lines.append(("  ✓ knowledge_graph        [ONLINE]", GREEN))
    lines.append(("  ✓ 11 scientist agents    [READY]", GREEN))
    lines.append(("", MUTED))
    lines.append(("System ready. All 60+ modules online.", GREEN))
    lines_list.append(list(lines))

    # Frame 7: Prompt appears
    lines = [
        ("╔══════════════════════════════════════════════════════╗", ORANGE),
        ("║     🧬  RUMI  —  Research & Unified Machine Int    ║", ORANGE),
        ("╚══════════════════════════════════════════════════════╝", ORANGE),
        ("", None),
        ("How can I help with your research today?", TEXT),
        ("", None),
        ("rumi > ", PROMPT_COLOR),
    ]
    lines_list.append(list(lines))

    # Frame 8-11: Typing pipeline command
    cmd = 'scientist_pipeline(action="run", topic="attention mechanisms in transformers")'
    for i in range(1, len(cmd) + 1):
        visible = cmd[:i]
        lines = [
            ("╔══════════════════════════════════════════════════════╗", ORANGE),
            ("║     🧬  RUMI  —  Research & Unified Machine Int    ║", ORANGE),
            ("╚══════════════════════════════════════════════════════╝", ORANGE),
            ("", None),
            ("How can I help with your research today?", TEXT),
            ("", None),
            (f"rumi > {visible}", PROMPT_COLOR),
        ]
        lines_list.append(list(lines))

    # Frame 12: Pipeline starts
    lines = [
        ("╔══════════════════════════════════════════════════════╗", ORANGE),
        ("╚══════════════════════════════════════════════════════╝", ORANGE),
        ("", None),
        ("[PIPELINE] Starting enhanced research pipeline...", CYAN),
        ("[PIPELINE] Topic: attention mechanisms in transformers", TEXT),
        ("", None),
        ("  Phase 1/12  Literature Review        [RUNNING]", YELLOW),
    ]
    lines_list.append(list(lines))

    # Frame 13: Phase progression
    phases = [
        ("Literature Review", "DONE", GREEN),
        ("Knowledge Graph Retrieval", "DONE", GREEN),
        ("Novelty Assessment", "DONE", GREEN),
        ("Hypothesis Generation", "DONE", GREEN),
        ("Experiment Design", "RUNNING", YELLOW),
    ]
    lines = [
        ("╔══════════════════════════════════════════════════════╗", ORANGE),
        ("╚══════════════════════════════════════════════════════╝", ORANGE),
        ("", None),
        ("[PIPELINE] Enhanced research pipeline — active learning loop", CYAN),
    ]
    for name, status, color in phases:
        icon = "✓" if status == "DONE" else "▶"
        lines.append((f"  Phase {icon}  {name:35s} [{status}]", color))
    lines.append(("", None))
    lines.append(("  Active learning: 3 experiment iterations queued", MUTED))
    lines_list.append(list(lines))

    # Frame 14: Results
    lines = [
        ("╔══════════════════════════════════════════════════════╗", ORANGE),
        ("╚══════════════════════════════════════════════════════╝", ORANGE),
        ("", None),
        ("[PIPELINE] Pipeline complete — 12/12 phases finished", GREEN),
        ("", None),
        ("  Key Findings:", TEXT),
        ("  • Attention heads specialize in specific syntactic patterns", TEXT),
        ("  • Multi-head attention shows emergent hierarchical processing", TEXT),
        ("  • Sparse attention reduces compute by 40% with minimal loss", TEXT),
        ("", None),
        ("  Paper draft generated: attention_mechanisms_2026.pdf", GREEN),
        ("  BibTeX citation ready. Knowledge graph updated.", MUTED),
        ("", None),
        ("rumi > ", PROMPT_COLOR),
    ]
    lines_list.append(list(lines))

    # Render frames
    for lines in lines_list:
        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)
        make_frame(draw, lines)
        frames.append(img)

    path = os.path.join(OUT_DIR, "rumi_demo.gif")
    base_dur = 60
    durs = []
    for i, _ in enumerate(frames):
        if i < 10:
            durs.append(60)
        elif i < len(frames) - 12:
            durs.append(40)
        elif i < len(frames) - 3:
            durs.append(200)
        else:
            durs.append(400)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durs,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Created: {path} ({os.path.getsize(path)} bytes)")
    return path


def create_pipeline_gif():
    frames = []
    phases = [
        ("1/12  Literature Review", "Searching arXiv, Semantic Scholar, PubMed...", 0),
        ("2/12  Knowledge Graph", "Extracting entities, building relationships...", 0),
        ("3/12  Novelty Assessment", "Comparing against 1,247 related papers...", 0),
        ("4/12  Hypothesis Generation", "GFlowNet tournament — 50 candidates...", 0),
        ("5/12  Experiment Design", "Bayesian optimal design — 3 iterations...", 0),
        ("6/12  Experiment Execution", "Running simulations, collecting data...", 0),
        ("7/12  Analysis", "Statistical testing, effect size, visualization...", 0),
        ("8/12  Reproducibility", "Cross-validation, sensitivity analysis...", 0),
        ("9/12  Paper Generation", "Writing abstract, methods, results...", 0),
        ("10/12 Peer Review", "Self-review: methodology, claims, citations...", 0),
        ("11/12 Knowledge Update", "Merging findings into knowledge graph...", 0),
        ("12/12 Self-Improvement", "Extracting lessons, updating strategies...", 0),
    ]

    # Opening frame
    lines = [
        ("╔══════════════════════════════════════════════════════╗", ORANGE),
        ("║   🔬  RUMI Scientist AI  —  12-Phase Pipeline       ║", ORANGE),
        ("╚══════════════════════════════════════════════════════╝", ORANGE),
    ]
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    make_frame(draw, lines)
    frames.append(img)

    # Progress frames
    for done_count in range(1, len(phases) + 1):
        lines = [
            ("╔══════════════════════════════════════════════════════╗", ORANGE),
            ("║   🔬  RUMI Scientist AI  —  12-Phase Pipeline       ║", ORANGE),
            ("╚══════════════════════════════════════════════════════╝", ORANGE),
        ]
        for i, (name, desc, _) in enumerate(phases):
            if i < done_count:
                icon = "✅"
                color = GREEN
            elif i == done_count:
                icon = "▶ "
                color = YELLOW
            else:
                icon = "  "
                color = MUTED
            status = "DONE" if i < done_count else ("RUNNING" if i == done_count else "PENDING")
            name_display = f"{icon} Phase {name}"
            lines.append((f"  {name_display:45s} [{status}]", color))
            if i == done_count and done_count < len(phases):
                lines.append((f"  {'':44s}{phases[done_count][1]}", MUTED))

        # Progress bar
        pct = done_count / len(phases)
        bar_w = 50
        filled = int(bar_w * pct)
        bar = "█" * filled + "░" * (bar_w - filled)
        lines.append(("", None))
        lines.append((f"  {bar}  {done_count}/{len(phases)} phases", GREEN))

        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)
        make_frame(draw, lines)
        frames.append(img)

    # Final frame with results
    lines = [
        ("╔══════════════════════════════════════════════════════╗", ORANGE),
        ("║   🔬  RUMI Scientist AI  —  12-Phase Pipeline       ║", ORANGE),
        ("╚══════════════════════════════════════════════════════╝", ORANGE),
        ("", None),
        ("  ✅  All 12 phases complete successfully!", GREEN),
        ("", None),
        ("  📄  Paper:    attention_mechanisms_2026.pdf", TEXT),
        ("  📊  Data:     4 experiment results, 12 charts", TEXT),
        ("  🧠  KG:       47 new entities, 128 relationships", TEXT),
        ("  🔄  Learning: 3 new strategies extracted", TEXT),
        ("", None),
        ("  Run complete. Ready for next research question.", GREEN),
        ("", None),
        ("rumi > ", PROMPT_COLOR),
    ]
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    make_frame(draw, lines)
    frames.append(img)

    path = os.path.join(OUT_DIR, "rumi_pipeline.gif")
    durs = [300] + [160] * len(phases) + [500]
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durs,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Created: {path} ({os.path.getsize(path)} bytes)")
    return path


def optimize_with_ffmpeg(input_path, output_path=None, max_colors=128):
    if output_path is None:
        name, ext = os.path.splitext(input_path)
        output_path = f"{name}_opt.gif"
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"split[s0][s1];[s0]palettegen=max_colors={max_colors}[p];[s1][p]paletteuse=dither=bayer",
        "-loop", "0", output_path
    ], capture_output=True)
    print(f"Optimized: {input_path} -> {output_path} ({os.path.getsize(output_path)} bytes)")


if __name__ == "__main__":
    gif1 = create_quickstart_gif()
    gif2 = create_pipeline_gif()
    optimize_with_ffmpeg(gif1, os.path.join(OUT_DIR, "rumi_demo.gif"))
    optimize_with_ffmpeg(gif2, os.path.join(OUT_DIR, "rumi_pipeline.gif"))
