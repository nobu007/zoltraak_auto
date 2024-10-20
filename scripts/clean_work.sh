#!/bin/bash

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "CURRENT_DIR=$CURRENT_DIR"
SAMPLES_DIR="$(cd "$CURRENT_DIR/../samples" && pwd)"
echo "SAMPLES_DIR=$SAMPLES_DIR"
WORK_DIR="$(cd "$CURRENT_DIR/../work" && pwd)"
echo "WORK_DIR=$WORK_DIR"

echo "rm -rf $WORK_DIR/*"
rm -rf "$WORK_DIR/"*
cp -p "$SAMPLES_DIR/destiny_InstantPromptBox.md" "$WORK_DIR/"
