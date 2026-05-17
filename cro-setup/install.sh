#!/usr/bin/env bash
# /cro-setup — installer
# Usage: bash install.sh

set -e

SKILL_DIR="$HOME/.claude/skills/cro-setup"

echo "=== /cro-setup — Installer ==="
echo ""

mkdir -p "$SKILL_DIR/scripts" "$SKILL_DIR/credentials" "$SKILL_DIR/configs"

echo "Setting up Python environment..."
# Prefer newest Python; google-auth dropped Python 3.9 support
for py in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$py" >/dev/null 2>&1; then
    PYBIN="$py"
    break
  fi
done
if [ -z "$PYBIN" ]; then
  echo "ERROR: Python 3.10+ required. Install via python.org or brew."
  exit 1
fi
echo "  Using: $($PYBIN --version)"
if [ ! -d "$SKILL_DIR/.venv" ]; then
  "$PYBIN" -m venv "$SKILL_DIR/.venv"
fi

echo "Installing dependencies..."
"$SKILL_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$SKILL_DIR/.venv/bin/pip" install --quiet -r "$SKILL_DIR/requirements.txt"

if [ ! -f "$SKILL_DIR/accounts.json" ]; then
  echo '{"default":null,"profiles":{}}' > "$SKILL_DIR/accounts.json"
fi

echo ""
echo "=== Cài đặt hoàn tất! ==="
echo ""
echo "Bước tiếp theo:"
echo "  1. GCP Console → tạo OAuth Client ID (Desktop app)"
echo "     Enable: Tag Manager API + Google Analytics Admin API"
echo "  2. Đăng ký OAuth client:"
echo "     cd $SKILL_DIR && .venv/bin/python manage_accounts.py set-oauth-client ~/Downloads/client_secret.json"
echo "  3. Gõ /cro-setup trong Claude Code"
