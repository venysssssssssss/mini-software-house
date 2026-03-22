#!/bin/sh

set -eu

run_cli=0

if [ "$#" -eq 0 ]; then
    set -- status
fi

case "$1" in
    create|status|info)
        run_cli=1
        set -- python -m src.cli "$@"
        ;;
    -*)
        run_cli=1
        set -- python -m src.cli "$@"
        ;;
esac

if [ "${run_cli}" -eq 1 ] && [ -n "${OLLAMA_HOST:-}" ] && [ "${WAIT_FOR_OLLAMA:-1}" = "1" ]; then
    ollama_api="${OLLAMA_HOST%/}/api/version"
    attempt=0
    max_attempts="${OLLAMA_MAX_ATTEMPTS:-30}"

    while ! curl --silent --fail --show-error "${ollama_api}" >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ "${attempt}" -ge "${max_attempts}" ]; then
            echo "Ollama unavailable at ${ollama_api} after ${max_attempts} attempts" >&2
            exit 1
        fi
        sleep 2
    done
fi

if [ "${run_cli}" -eq 1 ] && [ -n "${DEFAULT_MODEL:-}" ] && [ -n "${OLLAMA_HOST:-}" ]; then
    pull_api="${OLLAMA_HOST%/}/api/pull"
    curl --silent --fail --show-error \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"${DEFAULT_MODEL}\",\"stream\":false}" \
        "${pull_api}" >/dev/null 2>&1 || \
        echo "Skipping model pull for ${DEFAULT_MODEL}" >&2
fi

exec "$@"
