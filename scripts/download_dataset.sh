#!/usr/bin/env bash
# Fetch the upstream export without overwriting existing extracted files.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p data/downloads data/raw/iu_xray
archive=data/downloads/iu_xray.zip

if [[ ! -f "$archive" ]]; then
  if ! curl --fail --location --retry 3 \
    --output "${archive}.part" \
    "https://www.kaggle.com/api/v1/datasets/download/raddar/chest-xrays-indiana-university"; then
    echo "Download failed. Use the Kaggle dataset page, then save the ZIP as $archive." >&2
    echo "https://www.kaggle.com/datasets/raddar/chest-xrays-indiana-university" >&2
    exit 1
  fi
  mv "${archive}.part" "$archive"
fi

unzip -qn "$archive" -d data/raw/iu_xray
python3 scripts/verify_dataset.py
echo "Dataset verified. Next: run the README's radarena prepare command."
