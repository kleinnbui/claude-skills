#!/usr/bin/env bash
# Đóng gói skill thành 1 file zip để gửi cho nhân viên.
# Loại: .venv, __pycache__, accounts.json (profile của bạn), credentials/*.json (token cá nhân).
# Giữ: oauth_client.json để nhân viên không phải tự tạo OAuth client.
# Dùng: bash package.sh [đường/dẫn/ra.zip]
set -e

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$HOME/Desktop/seo-analyst.zip}"
STAGE="$(mktemp -d)"

rsync -a \
  --exclude='.venv/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='accounts.json' \
  --exclude='credentials/*.json' \
  --exclude='credentials/.discovery_result.json' \
  --exclude='data/*' \
  --exclude='.claude-plugin/' \
  --exclude='.DS_Store' \
  "$SRC/" "$STAGE/seo-analyst/"

mkdir -p "$STAGE/seo-analyst/credentials" "$STAGE/seo-analyst/data"
: > "$STAGE/seo-analyst/credentials/.gitkeep"
: > "$STAGE/seo-analyst/data/.gitkeep"

rm -f "$OUT"
(cd "$STAGE" && zip -r -q "$OUT" seo-analyst -x '*.DS_Store')
rm -rf "$STAGE"

echo "Đã tạo: $OUT"
if unzip -l "$OUT" | grep -qE 'credentials/[^/]+\.json|/accounts\.json'; then
  echo "CẢNH BÁO: gói có lẫn credential cá nhân — kiểm tra lại trước khi gửi." >&2
  exit 1
fi
echo "Đã kiểm tra: không lẫn token cá nhân hay accounts.json."
unzip -l "$OUT" | tail -3
