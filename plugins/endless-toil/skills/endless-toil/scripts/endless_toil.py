#!/usr/bin/env python3
"""Scan code and play theatrical pain noises based on heuristic quality signals."""

from __future__ import annotations

import argparse
import fnmatch
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path


TEXT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cfg",
    ".clj",
    ".cljs",
    ".cpp",
    ".cs",
    ".css",
    ".dart",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".json",
    ".kt",
    ".lua",
    ".md",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".vue",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".cache",
    ".git",
    ".hg",
    ".next",
    ".pytest_cache",
    ".svn",
    ".terraform",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

SKIP_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.lock",
    "go.sum",
}

PATTERNS = [
    ("debug logging", re.compile(r"\b(console\.log|debugger|print\(|println!|fmt\.Print|dump\(|var_dump)\b"), 1),
    ("todo/fixme", re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE), 1),
    ("ignored type/lint check", re.compile(r"(ts-ignore|type:\s*ignore|eslint-disable|pylint:\s*disable|rubocop:disable)"), 2),
    ("explicit any", re.compile(r"(:\s*any\b|as\s+any\b|Any\b)"), 1),
    ("dynamic execution", re.compile(r"\b(eval|exec|Function\s*\(|setTimeout\s*\(\s*['\"]|setInterval\s*\(\s*['\"])\b"), 6),
    ("shell execution", re.compile(r"\b(os\.system|subprocess\.(Popen|call|run)|child_process\.(exec|spawn))\b"), 3),
    ("broad exception", re.compile(r"\b(catch\s*\([^)]*\)\s*\{|except\s+(Exception|BaseException)?\s*:|rescue\s+StandardError)\b"), 2),
    ("empty catch/except", re.compile(r"(catch\s*\([^)]*\)\s*\{\s*\}|except[^\n:]*:\s*(pass)?\s*$)", re.MULTILINE), 4),
    ("secret-shaped literal", re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]"), 7),
    ("force unwrap/assertion", re.compile(r"(!\.|!!|unwrap\(\)|expect\(|assert\s+False)"), 2),
]


@dataclass
class Finding:
    label: str
    count: int
    points: int


@dataclass
class FileScore:
    path: Path
    score: int = 0
    level: str = "silence"
    findings: list[Finding] = field(default_factory=list)
    line_count: int = 0
    max_line_length: int = 0


@dataclass(frozen=True)
class ReactionLevel:
    name: str
    min_score: int
    duration: float
    base_freq: float
    wobble_hz: float
    bend: float
    roughness: float
    breathiness: float
    formants: tuple[tuple[float, float, float], ...]
    gain: float


SOUND_VERSION = "human-v2"
RECORDED_VERSION = "recorded-v1"
SKILL_DIR = Path(__file__).resolve().parents[1]
RECORDED_SAMPLE = SKILL_DIR / "assets" / "sounds" / "zombie_moan_public_domain.ogg"
RECORDED_VARIANTS = {
    "murmur": "aresample=44100,asetrate=44100*0.98,aresample=44100,atempo=1.08,volume=0.55,afade=t=in:st=0:d=0.04,afade=t=out:st=1.10:d=0.18",
    "groan": "aresample=44100,asetrate=44100*0.92,aresample=44100,atempo=1.00,volume=0.75,afade=t=in:st=0:d=0.04,afade=t=out:st=1.55:d=0.22",
    "moan": "aresample=44100,asetrate=44100*0.84,aresample=44100,atempo=0.96,volume=0.85,aecho=0.45:0.35:70:0.18,afade=t=in:st=0:d=0.04,afade=t=out:st=1.80:d=0.25",
    "wail": "aresample=44100,asetrate=44100*1.08,aresample=44100,atempo=0.95,volume=0.88,aecho=0.45:0.30:95:0.22,afade=t=in:st=0:d=0.03,afade=t=out:st=1.70:d=0.25",
    "howl": "aresample=44100,asetrate=44100*0.74,aresample=44100,atempo=0.90,volume=0.95,aecho=0.55:0.40:120:0.32,acompressor=threshold=-18dB:ratio=2.4:attack=12:release=180,afade=t=in:st=0:d=0.04,afade=t=out:st=2.15:d=0.30",
    "shriek": "aresample=44100,asetrate=44100*1.22,aresample=44100,atempo=0.93,volume=0.82,aecho=0.40:0.26:65:0.15,acompressor=threshold=-16dB:ratio=2.2:attack=6:release=120,afade=t=in:st=0:d=0.02,afade=t=out:st=1.45:d=0.20",
    "abyss": "aresample=44100,asetrate=44100*0.58,aresample=44100,atempo=0.82,volume=1.00,aecho=0.70:0.55:180|330:0.38|0.22,acompressor=threshold=-20dB:ratio=3.0:attack=18:release=260,afade=t=in:st=0:d=0.05,afade=t=out:st=3.00:d=0.35",
}

REACTION_LEVELS = (
    ReactionLevel("murmur", 4, 0.70, 132, 2.0, 10, 0.04, 0.10, ((360, 70, 1.0), (900, 110, 0.45), (2400, 180, 0.16)), 0.28),
    ReactionLevel("groan", 7, 1.05, 108, 2.6, 18, 0.07, 0.16, ((430, 85, 1.0), (980, 125, 0.55), (2550, 220, 0.18)), 0.31),
    ReactionLevel("moan", 12, 1.25, 142, 3.2, 24, 0.10, 0.18, ((610, 105, 1.0), (1120, 150, 0.48), (2600, 240, 0.20)), 0.32),
    ReactionLevel("wail", 18, 1.35, 172, 4.0, 34, 0.14, 0.22, ((720, 120, 1.0), (1220, 170, 0.52), (2750, 260, 0.24)), 0.32),
    ReactionLevel("howl", 25, 1.55, 96, 4.8, 42, 0.20, 0.28, ((500, 95, 1.0), (840, 130, 0.70), (2350, 260, 0.28)), 0.34),
    ReactionLevel("shriek", 32, 1.15, 230, 6.4, 64, 0.28, 0.34, ((780, 130, 1.0), (1680, 230, 0.70), (3100, 320, 0.34)), 0.31),
    ReactionLevel("abyss", 40, 1.85, 72, 5.7, 58, 0.26, 0.40, ((390, 90, 1.0), (760, 120, 0.82), (2100, 310, 0.30)), 0.36),
)


def iter_files(paths: list[Path], include_hidden: bool) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = raw_path.expanduser()
        if path.is_file():
            if is_candidate(path, include_hidden):
                files.append(path)
            continue
        if not path.exists():
            print(f"warning: path does not exist: {path}", file=sys.stderr)
            continue
        for root, dirnames, filenames in os.walk(path):
            dirnames[:] = [
                name
                for name in dirnames
                if (include_hidden or not name.startswith(".")) and name not in SKIP_DIRS
            ]
            for filename in filenames:
                candidate = Path(root) / filename
                if is_candidate(candidate, include_hidden):
                    files.append(candidate)
    return sorted(set(files))


def is_candidate(path: Path, include_hidden: bool) -> bool:
    if not include_hidden and path.name.startswith("."):
        return False
    if path.name in SKIP_FILES:
        return False
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    try:
        return path.stat().st_size <= 1_000_000
    except OSError:
        return False


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        print(f"warning: cannot read {path}: {exc}", file=sys.stderr)
        return None
    if b"\0" in data:
        return None
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def score_file(path: Path) -> FileScore | None:
    text = read_text(path)
    if text is None:
        return None

    result = FileScore(path=path)
    lines = text.splitlines()
    result.line_count = len(lines)
    result.max_line_length = max((len(line) for line in lines), default=0)

    if result.line_count > 800:
        add_finding(result, "very large file", 1, 5)
    elif result.line_count > 400:
        add_finding(result, "large file", 1, 3)

    long_lines = sum(1 for line in lines if len(line) > 140)
    if long_lines:
        add_finding(result, "long lines", long_lines, min(5, 1 + long_lines // 5))

    nesting = approximate_nesting(lines)
    if nesting >= 7:
        add_finding(result, "deep nesting", nesting, 5)
    elif nesting >= 5:
        add_finding(result, "deep nesting", nesting, 3)

    for label, pattern, weight in PATTERNS:
        count = len(pattern.findall(text))
        if count:
            add_finding(result, label, count, min(12, count * weight))

    result.level = level_for_score(result.score)
    return result


def add_finding(result: FileScore, label: str, count: int, points: int) -> None:
    result.score += points
    result.findings.append(Finding(label=label, count=count, points=points))


def approximate_nesting(lines: list[str]) -> int:
    max_depth = 0
    depth = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*")):
            continue
        depth -= stripped.count("}") + stripped.count(")")
        depth = max(depth, 0)
        max_depth = max(max_depth, depth)
        depth += stripped.count("{")
        if re.match(r"\b(if|for|while|try|catch|with|def|class|switch|case|elif|else)\b", stripped):
            depth += 1
    return max_depth


def level_for_score(score: int) -> str:
    for profile in reversed(REACTION_LEVELS):
        if score >= profile.min_score:
            return profile.name
    return "silence"


def make_sound(level: str, out_dir: Path) -> Path:
    recorded = make_recorded_sound(level, out_dir)
    if recorded is not None:
        return recorded
    return make_synth_sound(level, out_dir)


def make_recorded_sound(level: str, out_dir: Path) -> Path | None:
    ffmpeg = shutil.which("ffmpeg")
    filters = RECORDED_VARIANTS.get(level)
    if ffmpeg is None or filters is None or not RECORDED_SAMPLE.exists():
        return None

    filename = out_dir / f"endless-toil-{RECORDED_VERSION}-{level}.wav"
    if filename.exists():
        return filename

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(RECORDED_SAMPLE),
        "-map",
        "0:a:0",
        "-af",
        filters,
        "-ac",
        "1",
        "-ar",
        "44100",
        str(filename),
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        return None
    return filename if filename.exists() else None


def make_synth_sound(level: str, out_dir: Path) -> Path:
    filename = out_dir / f"endless-toil-{SOUND_VERSION}-{level}.wav"
    if filename.exists():
        return filename

    profile = profile_for_level(level)
    sample_rate = 44_100
    duration = profile.duration
    frames = int(sample_rate * duration)

    with wave.open(str(filename), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for i in range(frames):
            t = i / sample_rate
            amp = profile.gain * envelope(t, duration)
            value = amp * human_groan_sample(i, t, profile)
            wav.writeframes(struct.pack("<h", int(max(-1.0, min(1.0, value)) * 32767)))
    return filename


def profile_for_level(level: str) -> ReactionLevel:
    for profile in REACTION_LEVELS:
        if profile.name == level:
            return profile
    return REACTION_LEVELS[0]


def human_groan_sample(i: int, t: float, profile: ReactionLevel) -> float:
    pitch_drag = 1.0 - 0.12 * min(t / profile.duration, 1.0)
    wobble = math.sin(2 * math.pi * profile.wobble_hz * t)
    slow_lurch = math.sin(2 * math.pi * (profile.wobble_hz * 0.31) * t + 1.7)
    vibrato = 0.018 * math.sin(2 * math.pi * 5.2 * t + 0.4)
    crack = pitch_crack(t, profile)
    freq = max(45.0, profile.base_freq * pitch_drag * (1.0 + vibrato + crack) + profile.bend * wobble + 0.25 * profile.bend * slow_lurch)

    voice = voiced_vowel(t, freq, profile)
    subharmonic = 0.22 * math.sin(2 * math.pi * (freq * 0.5) * t + 0.8) if profile.base_freq < 120 else 0.0
    breath = profile.breathiness * aspirated_noise(i, t, profile)
    tremor = 0.82 + 0.18 * math.sin(2 * math.pi * (profile.wobble_hz * 1.8) * t)
    value = (voice + subharmonic) * tremor + breath
    return math.tanh(value * (1.35 + profile.roughness * 2.2))


def voiced_vowel(t: float, freq: float, profile: ReactionLevel) -> float:
    value = 0.0
    total_weight = 0.0
    max_harmonic = 30
    open_quotient = 0.62 + 0.08 * math.sin(2 * math.pi * profile.wobble_hz * 0.47 * t)
    for harmonic in range(1, max_harmonic + 1):
        harmonic_freq = freq * harmonic
        if harmonic_freq > 7000:
            break
        formant_gain = 0.10
        for center, width, gain in profile.formants:
            distance = (harmonic_freq - center) / width
            formant_gain += gain * math.exp(-0.5 * distance * distance)
        harmonic_rolloff = 1.0 / (harmonic ** 1.18)
        weight = formant_gain * harmonic_rolloff
        phase = harmonic * 0.19
        glottal_skew = 0.72 + 0.28 * math.sin(2 * math.pi * harmonic * open_quotient)
        value += weight * glottal_skew * math.sin(2 * math.pi * harmonic_freq * t + phase)
        total_weight += weight
    return value / max(total_weight * 0.55, 1.0)


def pitch_crack(t: float, profile: ReactionLevel) -> float:
    if profile.min_score < 18:
        return 0.0
    gate = max(0.0, math.sin(2 * math.pi * (profile.wobble_hz * 0.73) * t + 2.1))
    return 0.09 * profile.roughness * (gate ** 10) * math.sin(2 * math.pi * 38 * t)


def aspirated_noise(i: int, t: float, profile: ReactionLevel) -> float:
    hiss = deterministic_noise(i)
    flutter = 0.55 + 0.45 * math.sin(2 * math.pi * (profile.wobble_hz * 3.1) * t + 0.6)
    mouth = 0.0
    for center, width, gain in profile.formants:
        mouth += gain * math.sin(2 * math.pi * (center + width * deterministic_noise(i + int(center))) * t)
    return hiss * flutter * 0.75 + mouth * 0.05


def envelope(t: float, duration: float) -> float:
    attack = min(1.0, t / 0.08)
    release = min(1.0, (duration - t) / 0.18)
    return max(0.0, min(attack, release))


def deterministic_noise(i: int) -> float:
    value = (i * 1103515245 + 12345) & 0x7FFFFFFF
    return (value / 0x7FFFFFFF) * 2 - 1


def audio_player() -> list[str] | None:
    candidates = [
        ["afplay"],
        ["paplay"],
        ["aplay", "-q"],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
    ]
    for command in candidates:
        if shutil.which(command[0]):
            return command
    return None


def play(level: str, player: list[str], sound_dir: Path) -> None:
    sound = make_sound(level, sound_dir)
    try:
        subprocess.run([*player, str(sound)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as exc:
        print(f"warning: could not play {sound}: {exc}", file=sys.stderr)


def matches_any(path: Path, patterns: list[str]) -> bool:
    text = str(path)
    return any(fnmatch.fnmatch(text, pattern) or fnmatch.fnmatch(path.name, pattern) for pattern in patterns)


def format_findings(score: FileScore) -> str:
    if not score.findings:
        return "no obvious distress signals"
    ordered = sorted(score.findings, key=lambda item: item.points, reverse=True)
    return "; ".join(f"{item.label} x{item.count} (+{item.points})" for item in ordered[:4])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=["."], help="Files or directories to scan.")
    parser.add_argument("--dry-run", action="store_true", help="Print reactions without playing audio.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files and directories.")
    parser.add_argument("--max-files", type=int, default=40, help="Maximum scored files to print.")
    parser.add_argument("--max-sounds", type=int, default=12, help="Maximum reaction sounds to play.")
    parser.add_argument("--threshold", type=int, default=4, help="Minimum score required for an audible reaction.")
    parser.add_argument("--exclude", action="append", default=[], help="Glob pattern to exclude. Can be repeated.")
    args = parser.parse_args(argv)

    paths = [Path(path) for path in args.paths]
    files = [path for path in iter_files(paths, args.include_hidden) if not matches_any(path, args.exclude)]
    scores = [score for path in files if (score := score_file(path)) is not None and score.score >= args.threshold]
    scores.sort(key=lambda item: (item.score, item.line_count), reverse=True)

    print(f"Endless Toil scanned {len(files)} files; {len(scores)} triggered reactions.")
    for score in scores[: args.max_files]:
        print(f"{score.level.upper():7} {score.score:>3}  {score.path}  {format_findings(score)}")

    if not scores:
        print("Quiet. Suspiciously quiet.")
        return 0

    if args.dry_run:
        print("Dry run: audio skipped.")
        return 0

    player = audio_player()
    if player is None:
        print("No local audio player found; report printed without sound.")
        return 0

    sound_dir = Path(tempfile.gettempdir()) / "endless-toil-sounds"
    sound_dir.mkdir(parents=True, exist_ok=True)
    for score in scores[: args.max_sounds]:
        play(score.level, player, sound_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
