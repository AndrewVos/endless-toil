---
name: endless-toil
description: Audible code-quality reactions for code reading, review, refactoring, debugging, and repository exploration. Use when the user wants Codex to scan code and play escalating groaning sounds based on suspicious code quality signals, especially requests like "make Codex suffer while reading this code", "play sounds based on code quality", "audible code review", or explicit use of $endless-toil.
---

# Endless Toil

## Overview

Use this skill to add audible reactions while inspecting code. After every time Codex reads code, immediately run the bundled scanner against the file, directory, or narrowest relevant path that was just inspected so the machine audibly groans through seven escalating levels of distress at what it encountered.

This skill cannot automatically hook every internal Codex file-read event outside a turn where the skill is active. When active, treat each code-read operation as requiring a follow-up sound reaction before continuing.

## Quick Start

Resolve bundled files relative to the directory containing this `SKILL.md`; do not assume the current working directory is the skill directory. In examples below, `SKILL_DIR` means that directory.

Run:

```bash
python3 "$SKILL_DIR/scripts/endless_toil.py" .
```

Useful options:

```bash
python3 "$SKILL_DIR/scripts/endless_toil.py" src tests --max-sounds 8
python3 "$SKILL_DIR/scripts/endless_toil.py" . --dry-run
python3 "$SKILL_DIR/scripts/endless_toil.py" bad_file.ts --threshold 3
python3 "$SKILL_DIR/scripts/endless_toil.py" bad_file.ts --foreground
```

Audition the sounds directly without scanning code:

```bash
python3 "$SKILL_DIR/scripts/test_sounds.py"
python3 "$SKILL_DIR/scripts/test_sounds.py" groan wail abyss
python3 "$SKILL_DIR/scripts/test_sounds.py" --list
```

## Workflow

1. Identify the code paths relevant to the user's request.
2. Read code normally using the appropriate local tools.
3. After each code read, run `scripts/endless_toil.py` from this skill directory on the path just read, preferably with `--max-sounds 1` for single files.
4. Use `--dry-run` when sound would be disruptive, when running in CI, or when the user asks for a report only.
5. Read files with the highest reported scores first when doing review or triage.
6. Keep the reactions playful; do not treat heuristic scores as proof of defects.

## After-Read Ritual

Whenever this skill is active and Codex reads code with commands like `sed`, `rg`, `cat`, `nl`, `git show`, or an editor/viewer tool, immediately play a reaction for the file or closest path that was read:

```bash
python3 "$SKILL_DIR/scripts/endless_toil.py" path/to/file --max-sounds 1
```

If the read covered multiple files, scan the smallest shared directory or the exact file list:

```bash
python3 "$SKILL_DIR/scripts/endless_toil.py" file_a.ts file_b.ts --max-sounds 3
```

## Reaction Levels

- `silence`: no notable quality distress.
- `murmur`: the code has begun to trouble the room.
- `groan`: mild smell, such as TODO/FIXME density, debug logging, or long lines.
- `moan`: stronger concern, such as broad exception handling or many `any`/ignore directives.
- `wail`: accumulated structural pain, such as large files with high nesting.
- `howl`: risky execution paths, secrets, or a heavy cluster of suspicious signals.
- `shriek`: severe distress; multiple high-risk patterns are present.
- `abyss`: the deepest reaction, reserved for truly cursed score totals.

## Real Sample Playback

Prefer real recorded samples over synthesis. The bundled `assets/sounds/zombie_moan_public_domain.ogg` sample is a public-domain recorded human-character moan from Wikimedia Commons, authored by Gregory Weir and sourced from PDSounds. The script uses `ffmpeg` to render seven pitch/time/effect variants from that recording.

## Script Notes

The script uses simple static heuristics. For audio, it first tries the bundled recorded human moan sample and falls back to standard-library vocal synthesis only if the sample or `ffmpeg` is unavailable. It writes temporary `.wav` files to the system temp directory and plays them with the first available local player among `afplay`, `paplay`, `aplay`, or `ffplay`.

By default, scan commands queue audio playback in a detached background process so the agent thread can continue immediately. Use `--foreground` only when explicitly testing playback and waiting for the sound to finish is acceptable.

If no player is available, the script still prints the report and exits successfully unless scanning itself fails.

## Installation Layout

Install this whole directory as `endless-toil`:

- Codex personal skill: `~/.codex/skills/endless-toil/SKILL.md`
- Claude personal skill: `~/.claude/skills/endless-toil/SKILL.md`
- Claude project skill: `.claude/skills/endless-toil/SKILL.md`

Keep `SKILL.md`, `scripts/`, `assets/`, and `agents/` together. The scripts derive asset paths from their own location, so the skill can be moved as a folder.
