#!/usr/bin/env bash
# SEO Analyst Skill — installer
# Usage: bash install.sh

set -e

SKILL_DIR="$HOME/.claude/skills/seo-analyst"

echo "=== SEO Analyst Skill — Installer ==="
echo ""

# 1. Tạo thư mục đích
mkdir -p "$HOME/.claude/skills"

# 2. Copy files vào đúng vị trí (nếu chạy từ ngoài thư mục skill)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$SCRIPT_DIR" != "$SKILL_DIR" ]; then
  echo "Copying skill files to $SKILL_DIR ..."
  mkdir -p "$SKILL_DIR"
  cp -R "$SCRIPT_DIR/." "$SKILL_DIR/"
  # SKILL.md do plugin cung cấp — không để bản sao thành skill trùng tên
  rm -f "$SKILL_DIR/SKILL.md"
  rm -rf "$SKILL_DIR/.claude-plugin"
fi

# 3. Tạo Python venv — bắt buộc >= 3.10 (code dùng cú pháp `str | None`)
echo "Setting up Python environment..."
PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3 python; do
  command -v "$c" >/dev/null 2>&1 || continue
  if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ] && command -v py >/dev/null 2>&1; then
  py -3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null && PY="py -3"
fi
if [ -z "$PY" ]; then
  echo "LỖI: không tìm thấy Python 3.10+. macOS mặc định chỉ có 3.9 — cài từ python.org hoặc 'brew install python@3.13' rồi chạy lại." >&2
  exit 1
fi
echo "Dùng $PY ($($PY -V 2>&1))"
VENVPY="$SKILL_DIR/.venv/bin/python"
[ -x "$VENVPY" ] || VENVPY="$SKILL_DIR/.venv/Scripts/python.exe"
if [ -x "$VENVPY" ]; then
  "$VENVPY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null || {
    echo "venv cũ dùng Python < 3.10 — dựng lại."; rm -rf "$SKILL_DIR/.venv"; }
fi
if [ ! -x "$SKILL_DIR/.venv/bin/python" ] && [ ! -x "$SKILL_DIR/.venv/Scripts/python.exe" ]; then
  $PY -m venv "$SKILL_DIR/.venv"
fi

# 4. Install dependencies
echo "Installing dependencies..."
VPY="$SKILL_DIR/.venv/bin/python"
[ -x "$VPY" ] || VPY="$SKILL_DIR/.venv/Scripts/python.exe"
"$VPY" -m pip install --quiet --upgrade pip
"$VPY" -m pip install --quiet -r "$SKILL_DIR/requirements.txt"

# 5. Dọn symlink cũ trỏ vào file không còn tồn tại (bản cài đời trước)
if [ -L "$HOME/.claude/commands/seo-analyst.md" ] && [ ! -e "$HOME/.claude/commands/seo-analyst.md" ]; then
  rm -f "$HOME/.claude/commands/seo-analyst.md"
fi

# 6. Tạo accounts.json trống nếu chưa có
if [ ! -f "$SKILL_DIR/accounts.json" ]; then
  echo '{"shared_credentials": null, "default": null, "profiles": {}}' > "$SKILL_DIR/accounts.json"
fi

echo ""
echo "=== Cài đặt hoàn tất! ==="
echo ""
if [ -f "$SKILL_DIR/oauth_client.json" ]; then
  echo "OAuth client: đã có sẵn trong gói."
  echo "Gõ /seo-analyst trong Claude Code để bắt đầu — sẽ tự mở trình duyệt cho bạn đăng nhập Google 1 lần."
else
  echo "Bước tiếp theo:"
  echo "  1. Lấy OAuth client JSON từ Google Cloud Console"
  echo "     (Desktop app, enable: GA4 Data API + GA4 Admin API + Search Console API + Sheets API)"
  echo "  2. Chạy lệnh sau để đăng ký OAuth client:"
  echo "     cd $SKILL_DIR && bash run.sh manage_accounts.py set-oauth-client ~/Downloads/client_secret.json"
  echo ""
  echo "  3. Gõ /seo-analyst trong Claude Code để bắt đầu!"
fi
