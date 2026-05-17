#!/usr/bin/env bash
# SEO Analyst Skill — installer
# Usage: bash install.sh

set -e

SKILL_DIR="$HOME/.claude/skills/seo-analyst"
CMD_DIR="$HOME/.claude/commands"
SKILL_MD="$HOME/.claude/skills/seo-analyst.md"

echo "=== SEO Analyst Skill — Installer ==="
echo ""

# 1. Tạo thư mục đích
mkdir -p "$HOME/.claude/skills"
mkdir -p "$CMD_DIR"

# 2. Copy files vào đúng vị trí (nếu chạy từ ngoài thư mục skill)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$SCRIPT_DIR" != "$SKILL_DIR" ]; then
  echo "Copying skill files to $SKILL_DIR ..."
  cp -r "$SCRIPT_DIR/." "$SKILL_DIR/"
  # Copy skill instruction .md
  if [ -f "$SCRIPT_DIR/../seo-analyst.md" ]; then
    cp "$SCRIPT_DIR/../seo-analyst.md" "$SKILL_MD"
  fi
fi

# 3. Tạo Python venv
echo "Setting up Python environment..."
if [ ! -d "$SKILL_DIR/.venv" ]; then
  python3 -m venv "$SKILL_DIR/.venv"
fi

# 4. Install dependencies
echo "Installing dependencies..."
"$SKILL_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$SKILL_DIR/.venv/bin/pip" install --quiet -r "$SKILL_DIR/requirements.txt"

# 5. Tạo symlink slash command
if [ -L "$CMD_DIR/seo-analyst.md" ]; then
  rm "$CMD_DIR/seo-analyst.md"
fi
ln -s "$SKILL_MD" "$CMD_DIR/seo-analyst.md"

# 6. Tạo accounts.json trống nếu chưa có
if [ ! -f "$SKILL_DIR/accounts.json" ]; then
  echo '{"shared_credentials": null, "default": null, "profiles": {}}' > "$SKILL_DIR/accounts.json"
fi

echo ""
echo "=== Cài đặt hoàn tất! ==="
echo ""
echo "Bước tiếp theo:"
echo "  1. Lấy OAuth client JSON từ Google Cloud Console"
echo "     (Desktop app, enable: GA4 Data API + GA4 Admin API + Search Console API + Sheets API)"
echo "  2. Chạy lệnh sau để đăng ký OAuth client:"
echo "     cd $SKILL_DIR && .venv/bin/python manage_accounts.py set-oauth-client ~/Downloads/client_secret.json"
echo ""
echo "  3. Gõ /seo-analyst trong Claude Code để bắt đầu!"
