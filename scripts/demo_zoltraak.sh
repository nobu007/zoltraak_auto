#!/bin/bash

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "CURRENT_DIR=$CURRENT_DIR"
SAMPLES_DIR="$(cd "$CURRENT_DIR/../samples" && pwd)"
echo "SAMPLES_DIR=$SAMPLES_DIR"
ZOLTRAAK_DIR="$(cd "$CURRENT_DIR/.." && pwd)"
echo "ZOLTRAAK_DIR=$ZOLTRAAK_DIR"
WORK_DIR="$(cd "$ZOLTRAAK_DIR/work" && pwd)"
echo "WORK_DIR=$WORK_DIR"

cd "$WORK_DIR"
zoltraak "$ZOLTRAAK_DIR/InstantPromptBox/README_JA.md" -n InstantPromptBox -ml 1 -mle 9
