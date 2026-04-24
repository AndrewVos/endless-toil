#!/usr/bin/env bash
set -euo pipefail

base="plugins/endless-toil/skills/endless-toil/assets/sounds/zombie_moan_public_domain.ogg"
out_dir="plugins/endless-toil/skills/endless-toil/assets/sounds/generated"

mkdir -p "$out_dir"

while IFS=$'\t' read -r level filter; do
  ffmpeg -hide_banner -loglevel error -y \
    -i "$base" \
    -map 0:a:0 \
    -af "$filter" \
    -ac 1 \
    -ar 44100 \
    "$out_dir/$level.wav"
done <<'EOF'
murmur	aresample=44100,asetrate=44100*0.98,aresample=44100,atempo=1.08,volume=0.55,afade=t=in:st=0:d=0.04,afade=t=out:st=1.10:d=0.18
groan	aresample=44100,asetrate=44100*0.92,aresample=44100,atempo=1.00,volume=0.75,afade=t=in:st=0:d=0.04,afade=t=out:st=1.55:d=0.22
moan	aresample=44100,asetrate=44100*0.84,aresample=44100,atempo=0.96,volume=0.85,aecho=0.45:0.35:70:0.18,afade=t=in:st=0:d=0.04,afade=t=out:st=1.80:d=0.25
wail	aresample=44100,asetrate=44100*1.08,aresample=44100,atempo=0.95,volume=0.88,aecho=0.45:0.30:95:0.22,afade=t=in:st=0:d=0.03,afade=t=out:st=1.70:d=0.25
howl	aresample=44100,asetrate=44100*0.74,aresample=44100,atempo=0.90,volume=0.95,aecho=0.55:0.40:120:0.32,acompressor=threshold=-18dB:ratio=2.4:attack=12:release=180,afade=t=in:st=0:d=0.04,afade=t=out:st=2.15:d=0.30
shriek	aresample=44100,asetrate=44100*1.22,aresample=44100,atempo=0.93,volume=0.82,aecho=0.40:0.26:65:0.15,acompressor=threshold=-16dB:ratio=2.2:attack=6:release=120,afade=t=in:st=0:d=0.02,afade=t=out:st=1.45:d=0.20
abyss	aresample=44100,asetrate=44100*0.58,aresample=44100,atempo=0.82,volume=1.00,aecho=0.70:0.55:180|330:0.38|0.22,acompressor=threshold=-20dB:ratio=3.0:attack=18:release=260,afade=t=in:st=0:d=0.05,afade=t=out:st=3.00:d=0.35
EOF
