# Endless Toil

Endless Toil is a Codex and Claude Code plugin that adds an `endless-toil` skill. When active, the skill scans recently read code and plays escalating recorded human groans based on code-quality distress signals.

This repository is laid out as a local plugin marketplace for both Codex and Claude Code:

```text
.agents/plugins/marketplace.json
.claude-plugin/marketplace.json
plugins/endless-toil/.codex-plugin/plugin.json
plugins/endless-toil/.claude-plugin/plugin.json
plugins/endless-toil/skills/endless-toil/SKILL.md
plugins/endless-toil/skills/endless-toil/scripts/endless_toil.py
plugins/endless-toil/skills/endless-toil/scripts/test_sounds.py
plugins/endless-toil/skills/endless-toil/assets/sounds/zombie_moan_public_domain.ogg
```

## Use In Codex CLI

From Codex CLI, add this repository as a local marketplace root:

```bash
codex plugin marketplace add .
```

Then open the plugin browser:

```text
/plugins
```

Choose the `Endless Toil` marketplace, install `Endless Toil`, restart Codex if needed, and invoke the plugin or its bundled skill from a new thread.

## Use In Codex Desktop

Clone this repository somewhere on your machine, then open that folder in Codex Desktop.

1. Open `Plugins`.
2. Search or browse for `Endless Toil`, then open its details.
3. Select the plus button or `Add to Codex`.
4. If prompted, complete any setup steps.
5. Start a new thread and ask Codex to use `Endless Toil`.

## Use In Claude CLI

Clone this repository somewhere on your machine, then start Claude from this repository root.

Add this repository as a local plugin marketplace:

```text
/plugin marketplace add .
```

Then install the plugin:

```text
/plugin install endless-toil@endless-toil
```

Restart Claude Code if prompted, then invoke the bundled skill:

```text
/endless-toil
```

## Test Sounds

From this repository root:

```bash
python3 plugins/endless-toil/skills/endless-toil/scripts/test_sounds.py --list
python3 plugins/endless-toil/skills/endless-toil/scripts/test_sounds.py groan wail abyss
```

## Source

Plugin structure and marketplace layout follow the OpenAI Codex and Claude Code plugin docs:

https://developers.openai.com/codex/plugins
https://code.claude.com/docs/en/plugins
