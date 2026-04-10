#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python -m venv "${ROOT_DIR}/.venv"
source "${ROOT_DIR}/.venv/bin/activate"
pip install --upgrade pip
pip install -r "${ROOT_DIR}/requirements.txt"

pushd "${ROOT_DIR}/frontend" >/dev/null
npm install
popd >/dev/null

echo "Environment bootstrapped."
echo "Backend: source .venv/bin/activate && uvicorn backend.main:app --reload"
echo "Frontend: cd frontend && npm start"

