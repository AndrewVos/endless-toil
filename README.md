# Endless Toil

Endless Toil is a Codex plugin that adds an `endless-toil` skill. When active, the skill scans recently read code and plays escalating recorded human groans based on code-quality distress signals.

This repository is laid out as a local Codex plugin marketplace, following the OpenAI Codex plugin docs:

```text
.agents/plugins/marketplace.json
plugins/endless-toil/.codex-plugin/plugin.json
plugins/endless-toil/skills/endless-toil/SKILL.md
plugins/endless-toil/skills/endless-toil/scripts/endless_toil.py
plugins/endless-toil/skills/endless-toil/scripts/test_sounds.py
plugins/endless-toil/skills/endless-toil/assets/sounds/zombie_moan_public_domain.ogg
```

## Use In Codex

From Codex CLI, add this repository as a local marketplace root:

```bash
codex plugin marketplace add .
```

Then open the plugin browser:

```text
/plugins
```

Choose the `Endless Toil` marketplace, install `Endless Toil`, restart Codex if needed, and invoke the plugin or its bundled skill from a new thread.

## Test Sounds

From this repository root:

```bash
python3 plugins/endless-toil/skills/endless-toil/scripts/test_sounds.py --list
python3 plugins/endless-toil/skills/endless-toil/scripts/test_sounds.py groan wail abyss
```

## Source

Plugin structure and marketplace layout follow the OpenAI Codex plugin docs:

https://developers.openai.com/codex/plugins
