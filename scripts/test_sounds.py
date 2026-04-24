#!/usr/bin/env python3
"""Audition Endless Toil reaction sounds without scanning code."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import endless_toil


LEVELS = [profile.name for profile in endless_toil.REACTION_LEVELS]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("levels", nargs="*", help=f"Levels to play. Defaults to all: {', '.join(LEVELS)}")
    parser.add_argument("--list", action="store_true", help="List available levels and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Generate sounds and print paths without playing.")
    parser.add_argument("--pause", type=float, default=0.25, help="Seconds to pause between sounds.")
    parser.add_argument("--out-dir", default=None, help="Directory for generated WAV files. Defaults to system temp.")
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(LEVELS))
        return 0

    levels = args.levels or LEVELS
    unknown = [level for level in levels if level not in LEVELS]
    if unknown:
        print(f"Unknown level(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Available levels: {', '.join(LEVELS)}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir).expanduser() if args.out_dir else Path(tempfile.gettempdir()) / "endless-toil-sounds"
    out_dir.mkdir(parents=True, exist_ok=True)

    player = None if args.dry_run else endless_toil.audio_player()
    if player is None and not args.dry_run:
        print("No audio player found; generated files will be listed without playback.", file=sys.stderr)

    for level in levels:
        sound = endless_toil.make_sound(level, out_dir)
        print(f"{level:7} {sound}")
        if player is not None:
            subprocess.run([*player, str(sound)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(max(0.0, args.pause))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
