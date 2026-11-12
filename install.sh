#!/usr/bin/env bash
# Instala las mascotas de este repo para Petdex Desktop, Codex y OpenPets.
# Uso:
#   ./install.sh                         -> instala todas (guante-verde y angel-gaitan)
#   ./install.sh angel-gaitan            -> instala solo esa
#   ./install.sh --desinstalar           -> quita todas
#   ./install.sh --desinstalar guante-verde
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PETS_DIR="$REPO_DIR/pets"
DESTINOS_BASE=(
  "$HOME/.petdex/pets"
  "${CODEX_HOME:-$HOME/.codex}/pets"
)

modo="instalar"
if [[ "${1:-}" == "--desinstalar" ]]; then
  modo="desinstalar"
  shift
fi

ids=()
if [[ $# -gt 0 ]]; then
  ids=("$@")
else
  while IFS= read -r dir; do
    ids+=("$(basename "$dir")")
  done < <(find "$PETS_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
fi

for id in "${ids[@]}"; do
  src="$PETS_DIR/$id"
  if [[ ! -f "$src/pet.json" || ! -f "$src/spritesheet.webp" ]]; then
    echo "Error: no existe la mascota '$id'. Disponibles:" >&2
    find "$PETS_DIR" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort >&2
    exit 1
  fi
  for base in "${DESTINOS_BASE[@]}"; do
    dest="$base/$id"
    if [[ "$modo" == "desinstalar" ]]; then
      if [[ -d "$dest" ]]; then
        rm -f "$dest/pet.json" "$dest/spritesheet.webp"
        rmdir "$dest" 2>/dev/null || true
        echo "Quitada $id de $base"
      fi
    else
      mkdir -p "$dest"
      cp "$src/pet.json" "$src/spritesheet.webp" "$dest/"
      echo "Instalada $id en $base"
    fi
  done
done

if [[ "$modo" == "instalar" ]]; then
  cat <<'EOF'

Listo. Para verla en pantalla y que reaccione a Claude Code:
  1. Descarga Petdex Desktop: https://petdex.dev/download
  2. Ábrelo, pon el ratón encima de la mascota y pulsa Cmd+, (Ctrl+, en Windows/Linux).
  3. En "Pets" elige "Guante Verde" o "Ángel Gaitán".
  4. En "Agents" pulsa conectar en Claude Code.
EOF
fi
