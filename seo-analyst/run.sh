#!/usr/bin/env bash
# Chọn đúng interpreter của venv: macOS/Linux dùng .venv/bin, Windows (Git Bash) dùng .venv/Scripts.
# Mọi lệnh trong SKILL.md gọi qua wrapper này để chạy được trên cả hai nền tảng.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for p in "$DIR/.venv/bin/python" "$DIR/.venv/Scripts/python.exe"; do
  if [ -x "$p" ]; then exec "$p" "$@"; fi
done
echo "NOT_BOOTSTRAPPED: chưa có .venv trong $DIR — chạy lại Bước 0 của skill." >&2
exit 1
