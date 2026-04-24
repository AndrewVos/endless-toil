# Endless Toil

Hear your agent suffer through your code.

![Endless Toil](assets/endless-toil.png)

Endless Toil runs alongside your coding agent in real time, playing escalating recorded human groans as the code it reads starts to look more cursed.

Note: installing the plugin does not make it auto-activate in every thread by default. Start a new thread and ask Codex or Claude to use `Endless Toil`.

## Use In Codex Desktop

Clone this repository somewhere on your machine, then open that directory in Codex Desktop.

1. Open `Plugins`.
2. Search or browse for `Endless Toil`, then open its details.
3. Select the plus button or `Add to Codex`.
4. If prompted, complete any setup steps.
5. Start a new thread and ask Codex to use `Endless Toil`.

## Use In Codex CLI

From Codex CLI, add this repository as a local marketplace root:

```bash
codex plugin marketplace add ./
```

Then open the plugin browser:

```text
/plugins
```

Choose the `Endless Toil` marketplace, install `Endless Toil`, restart Codex if needed, and invoke the plugin or its bundled skill from a new thread.

## Use In Claude CLI

Clone this repository somewhere on your machine, then start Claude from this repository root.

Add this repository as a local plugin marketplace:

```text
/plugin marketplace add ./
```

Then install the plugin:

```text
/plugin install endless-toil@endless-toil
```

Restart Claude Code if prompted, then invoke the bundled skill:

```text
/endless-toil
```

## Use In Cursor

Clone this repository somewhere on your machine, then add it as a local Cursor plugin marketplace from Cursor.

Install `Endless Toil`, restart Cursor if prompted, then ask Cursor Agent to use the bundled skill:

```text
Use endless-toil while reading this code.
```

## Test Sounds

From this repository root:

```bash
python3 plugins/endless-toil/skills/endless-toil/scripts/test_sounds.py --list
python3 plugins/endless-toil/skills/endless-toil/scripts/test_sounds.py groan wail abyss
```

## Requirements

- Python 3.10+
- A local audio player: `afplay` on macOS, or `paplay`, `aplay`, or `ffplay` on Linux

If an audio player is unavailable, Endless Toil still prints scan results, but it will not play sounds.

## Source

Plugin structure and marketplace layout follow the OpenAI Codex and Claude Code plugin docs:

https://developers.openai.com/codex/plugins
https://code.claude.com/docs/en/plugins
https://github.com/cursor/plugins
