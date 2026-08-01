set dotenv-load := true

# List available recipes.
help:
  #!/usr/bin/env bash
  set -euo pipefail
  just --list

# Run web UI with automatic reload.
dev:
  #!/usr/bin/env bash
  set -euo pipefail
  export OCPM_SOCKS_PORT="${OCPM_SOCKS_PORT:-1080}"
  export OCPM_HTTP_PORT="${OCPM_HTTP_PORT:-8080}"
  export OCPM_WEBUI_PORT="${OCPM_WEBUI_PORT:-8081}"
  cd glider
  glider -config glider.conf &
  glider_pid=$!
  cleanup() {
    trap - EXIT INT TERM
    kill "$glider_pid" 2>/dev/null || true
    wait "$glider_pid" 2>/dev/null || true
  }
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  cd ../webapp
  uv run uvicorn app:app --reload --host 0.0.0.0 --port "$OCPM_WEBUI_PORT"

# Run focused module tests.
test:
  #!/usr/bin/env bash
  set -euo pipefail
  cd webapp
  uv run python -m unittest discover -s . -p '*_test.py'

# Start Compose VPN stack.
start:
  #!/usr/bin/env bash
  set -euo pipefail
  docker compose up -d

# Stop Compose VPN stack.
stop:
  #!/usr/bin/env bash
  set -euo pipefail
  docker compose down

# Remove Compose containers, networks, and volumes.
clean:
  #!/usr/bin/env bash
  set -euo pipefail
  docker compose down --volumes --remove-orphans
