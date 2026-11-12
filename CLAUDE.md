# Instrucciones para Claude Code

Este repo contiene una mascota de escritorio, "Guante Verde" (`pets/guante-verde/`), en el formato
de Codex / [Petdex](https://github.com/crafter-station/petdex): `pet.json` + `spritesheet.webp`
(atlas 8x9, celdas de 192x208, 1536x1872 px).

## Cuando el usuario pida instalar la mascota

1. Si no estás dentro del repo, clónalo:
   `gh repo clone armandofcom/claude-pets-angel && cd claude-pets-angel`
2. Ejecuta `./install.sh`. Copia `pet.json` y `spritesheet.webp` a:
   - `~/.petdex/pets/guante-verde/` (Petdex Desktop)
   - `~/.codex/pets/guante-verde/` (Codex y OpenPets)
3. Comprueba que existen los dos archivos en ambos destinos (`ls -la`).
4. Explica al usuario el último paso, que es suyo y no tuyo:
   descargar Petdex Desktop desde https://petdex.dev/download, abrirlo, pulsar Cmd+, sobre la mascota,
   elegir "Guante Verde" en **Pets** y conectar **Claude Code** en **Agents**.
   No descargues ni instales la app sin que el usuario lo confirme.

Alternativa: OpenPets (https://github.com/OpenPetsHQ/openpets) también lee `~/.codex/pets/`.

## Desinstalar

`./install.sh --desinstalar`

## Regenerar el atlas

```sh
python3 -m venv .venv && .venv/bin/pip install pillow
.venv/bin/python tools/generar_atlas.py --logo tools/guante-verde-logo.webp --salida ./salida
cp salida/spritesheet.webp pets/guante-verde/
```

El script falla (exit 1) si algún frame se sale de su celda.

## Reglas

- El guante es el logo de Ángel Gaitán. No lo publiques en la galería pública de Petdex
  (`petdex submit`) ni en otro sitio sin permiso expreso del usuario.
- No cambies el orden de las filas del atlas: idle, running-right, running-left, waving,
  jumping, failed, waiting, running, review.
