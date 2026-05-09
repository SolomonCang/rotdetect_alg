#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$ROOT_DIR/.venv"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

print_step() {
  echo
  echo "==> $1"
}

if [[ ! -d "$BACKEND_DIR" || ! -d "$FRONTEND_DIR" ]]; then
  echo "Error: backend or frontend directory not found."
  echo "Please run this script from the repository root."
  exit 1
fi

if ! command_exists python3; then
  echo "Error: python3 is not installed."
  exit 1
fi

if ! command_exists npm; then
  echo "Error: npm is not installed."
  exit 1
fi

print_step "Installing backend dependencies"
if command_exists uv; then
  echo "Using uv sync in backend/."
  (
    cd "$BACKEND_DIR"
    uv sync
  )
else
  echo "uv not found. Falling back to pip + editable install."

  if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi

  # Activate local virtual environment for pip fallback install.
  source "$VENV_DIR/bin/activate"
  python -m pip install --upgrade pip
  python -m pip install -e "$BACKEND_DIR"
fi

print_step "Installing frontend dependencies"
(
  cd "$FRONTEND_DIR"
  npm install
)

print_step "All dependencies installed"
echo "Done. You can start the project with: python3 start_rotdetect.py"
