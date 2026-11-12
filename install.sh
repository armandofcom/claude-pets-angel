#!/usr/bin/env bash
# Instala la mascota "Guante Verde" para Petdex Desktop, Codex y OpenPets.
# Uso: ./install.sh            -> instala
#      ./install.sh --desinstalar -> la quita
set -euo pipefail

PET_ID="guante-verde"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO_DIR/pets/$PET_ID"
DESTINOS=(
  "$HOME/.petdex/pets/$PET_ID"
  "${CODEX_HOME:-$HOME/.codex}/pets/$PET_ID"
)

if [[ "${1:-}" == "--desinstalar" ]]; then
  for dest in "${DESTINOS[@]}"; do
    if [[ -d "$dest" ]]; then
      rm -f "$dest/pet.json" "$dest/spritesheet.webp"
      rmdir "$dest" 2>/dev/null || true
      echo "Quitada de $dest"
    fi
  done
  exit 0
fi

for f in pet.json spritesheet.webp; do
  if [[ ! -f "$SRC/$f" ]]; then
    echo "Error: falta $SRC/$f. Clona el repo completo y vuelve a intentarlo." >&2
    exit 1
  fi
done

for dest in "${DESTINOS[@]}"; do
  mkdir -p "$dest"
  cp "$SRC/pet.json" "$SRC/spritesheet.webp" "$dest/"
  echo "Instalada en $dest"
done

cat <<'EOF'

Listo. Para verla en pantalla y que reaccione a Claude Code:
  1. Descarga Petdex Desktop: https://petdex.dev/download
  2. Ábrelo, pon el ratón encima de la mascota y pulsa Cmd+, (Ctrl+, en Windows/Linux).
  3. En "Pets" elige "Guante Verde".
  4. En "Agents" pulsa conectar en Claude Code.
EOF
