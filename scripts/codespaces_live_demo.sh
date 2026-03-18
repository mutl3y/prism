#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/debug_readmes/codespaces_demo"
ROLE_PATH="${ROOT_DIR}/src/prism/tests/roles/enhanced_mock_role"

PYTHON_BIN="$(command -v python || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "Neither 'python' nor 'python3' is available in PATH." >&2
  exit 127
fi

# Prefer installed package, but fall back to source tree when needed.
if ! "${PYTHON_BIN}" -c "import prism" >/dev/null 2>&1; then
  export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
fi

quick_mode=false
serve_mode=false
port="${PORT:-8000}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick)
      quick_mode=true
      shift
      ;;
    --serve)
      serve_mode=true
      shift
      ;;
    --port)
      port="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "${OUTPUT_DIR}"

"${PYTHON_BIN}" -m prism.cli "${ROLE_PATH}" -o "${OUTPUT_DIR}/README.md"
"${PYTHON_BIN}" -m prism.cli "${ROLE_PATH}" --format json -o "${OUTPUT_DIR}/README.json"

if [[ "${quick_mode}" != true ]]; then
  "${PYTHON_BIN}" -m prism.cli "${ROLE_PATH}" --format html -o "${OUTPUT_DIR}/README.html"
fi

echo "Prism live demo generated:"
echo "- ${OUTPUT_DIR}/README.md"
echo "- ${OUTPUT_DIR}/README.json"
if [[ "${quick_mode}" != true ]]; then
  echo "- ${OUTPUT_DIR}/README.html"
fi

if [[ "${serve_mode}" == true ]]; then
  if [[ ! -f "${OUTPUT_DIR}/README.html" ]]; then
    "${PYTHON_BIN}" -m prism.cli "${ROLE_PATH}" --format html -o "${OUTPUT_DIR}/README.html"
  fi
  echo "Serving ${OUTPUT_DIR} at http://0.0.0.0:${port}"
  cd "${OUTPUT_DIR}"
  exec "${PYTHON_BIN}" -m http.server "${port}"
fi
