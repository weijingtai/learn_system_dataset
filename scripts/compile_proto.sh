#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PROTOC_BIN="$(which protoc || echo "/opt/homebrew/opt/protobuf@3/bin/protoc")"

if [ ! -x "${PROTOC_BIN}" ]; then
  echo "Error: protoc binary not found."
  exit 1
fi

mkdir -p console_backend/generated
"${PROTOC_BIN}" --python_out=console_backend/generated -I. proto/console/v1/*.proto

touch console_backend/generated/__init__.py
touch console_backend/generated/proto/__init__.py
touch console_backend/generated/proto/console/__init__.py
touch console_backend/generated/proto/console/v1/__init__.py

echo "Protobuf compiled successfully to console_backend/generated/"
