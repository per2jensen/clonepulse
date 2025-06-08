#!/bin/bash
# SPDX-License-Identifier: MIT

set -euo pipefail


UPLOAD=false


# === Helpers ===
red()   { echo -e "\033[1;31m$*\033[0m"; }
green() { echo -e "\033[1;32m$*\033[0m"; }


# === Parse arguments ===
for arg in "$@"; do
    case $arg in
        --upload-to-pypi)
            UPLOAD=true
            ;;
        *)
            echo "❌ Unknown option: $arg"
            echo "Usage: $0 [--upload-to-pypi]"
            exit 1
            ;;
    esac
done


# === Setup virtual environment ===
python3 -m venv venv
source venv/bin/activate

echo "🔧 Creating venv in: $VIRTUAL_ENV"
pip install --upgrade pip

# === Install dev & packaging tools ===
pip install -e ".[dev,packaging]"

VERSION=$(hatch version)
echo "✅ Installed project in editable mode with dev and packaging tools."

# === Clean old builds ===
DIST_DIR="dist"
rm -rf "$DIST_DIR"
echo "🧹 Removed old $DIST_DIR/"

# === Build package using Hatch ===
hatch build

echo "📦 Build complete. Artifacts:"
ls -lh "$DIST_DIR"


# === Validate package before upload ===
echo "🔍 Validating distributions..."
twine check dist/* || {
    red "❌ Package validation failed."
    exit 1
}

echo Version: ${VERSION}

# === Upload to PyPI if requested ===
if $UPLOAD; then
    green "Uploading to PyPI..."
    if twine upload "$DIST_DIR"/*; then
        green "🎉 Done: Version $VERSION uploaded successfully"
    else
        red "❌ Upload failed: twine returned non-zero exit code"
        exit 1
    fi
else
    green "Dry run: Skipping upload to PyPI"
    echo  "To upload, run:"
    echo  "  ./release.sh --upload-to-pypi"
fi
