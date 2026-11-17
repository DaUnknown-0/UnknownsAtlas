#!/usr/bin/env bash
# Freeplay-Test aus dieser Kopie. Exit 3: Spiel laeuft bereits, kein Testeinsatz.
# EXTRA setzt Config-Werte. OUTDIR liegt im Projekt oder im freigegebenen Auditordner.
set -eu
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if command -v cygpath >/dev/null 2>&1; then HERE="$(cygpath -w "$HERE")"; fi
exec python "$HERE/maptest_runner.py" "$@"
