#!/usr/bin/env python3
"""Scan code and play theatrical pain noises based on heuristic quality signals."""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile
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


SKILL_DIR = Path(__file__).resolve().parents[1]
GENERATED_SOUND_DIR = SKILL_DIR / "assets" / "sounds" / "generated"

REACTION_LEVELS = (
    ReactionLevel("murmur", 4),
    ReactionLevel("groan", 7),
    ReactionLevel("moan", 12),
    ReactionLevel("wail", 18),
    ReactionLevel("howl", 25),
    ReactionLevel("shriek", 32),
    ReactionLevel("abyss", 40),
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
    sound = GENERATED_SOUND_DIR / f"{level}.wav"
    if sound.exists():
        return sound
    raise RuntimeError(f"bundled sound is missing for level: {level}")


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
    try:
        sound = make_sound(level, sound_dir)
        subprocess.run([*player, str(sound)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, RuntimeError) as exc:
        print(f"warning: could not play {level}: {exc}", file=sys.stderr)


def queue_play(level: str, player: list[str], sound_dir: Path) -> bool:
    try:
        sound = make_sound(level, sound_dir)
        subprocess.Popen(
            [*player, str(sound)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
    except (OSError, RuntimeError):
        return False
    return True


def play_levels(levels: list[str], sound_dir: Path) -> int:
    player = audio_player()
    if player is None:
        return 1
    sound_dir.mkdir(parents=True, exist_ok=True)
    for level in levels:
        play(level, player, sound_dir)
    return 0


def queue_background_playback(levels: list[str], sound_dir: Path) -> int:
    if not levels:
        return 0
    player = audio_player()
    if player is None:
        return 0
    sound_dir.mkdir(parents=True, exist_ok=True)
    queued = 0
    for level in levels:
        if queue_play(level, player, sound_dir):
            queued += 1
    return queued


def queue_background_worker(levels: list[str], sound_dir: Path) -> bool:
    if not levels:
        return False
    python = sys.executable or shutil.which("python3") or "python3"
    log_path = Path(tempfile.gettempdir()) / "endless-toil-background.log"
    command = [python, str(Path(__file__).resolve()), "--play-levels", *levels, "--sound-dir", str(sound_dir)]
    try:
        log = log_path.open("ab")
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True)
    except OSError:
        return False
    return True


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
    parser.add_argument("--foreground", action="store_true", help="Play audio before exiting instead of queuing it in the background.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files and directories.")
    parser.add_argument("--max-files", type=int, default=40, help="Maximum scored files to print.")
    parser.add_argument("--max-sounds", type=int, default=12, help="Maximum reaction sounds to play.")
    parser.add_argument("--threshold", type=int, default=4, help="Minimum score required for an audible reaction.")
    parser.add_argument("--exclude", action="append", default=[], help="Glob pattern to exclude. Can be repeated.")
    parser.add_argument("--play-levels", nargs="+", help=argparse.SUPPRESS)
    parser.add_argument("--sound-dir", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    sound_dir = Path(args.sound_dir).expanduser() if args.sound_dir else Path(tempfile.gettempdir()) / "endless-toil-sounds"
    if args.play_levels:
        valid_levels = {profile.name for profile in REACTION_LEVELS}
        levels = [level for level in args.play_levels if level in valid_levels]
        return play_levels(levels, sound_dir)

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

    if audio_player() is None:
        print("No local audio player found; report printed without sound.")
        return 0

    levels = [score.level for score in scores[: args.max_sounds]]
    if args.foreground:
        play_levels(levels, sound_dir)
    else:
        queued = queue_background_playback(levels, sound_dir)
        if queued:
            print("Audio queued in background.")
        elif queue_background_worker(levels, sound_dir):
            print("Audio queued in background worker.")
        else:
            print("Could not queue background audio; playing in foreground.")
            play_levels(levels, sound_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
