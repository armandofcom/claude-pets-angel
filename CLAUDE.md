# Instrucciones para Claude Code

Este repo contiene dos mascotas de escritorio en el formato de Codex /
[Petdex](https://github.com/crafter-station/petdex) (`pet.json` + `spritesheet.webp`, atlas 8x9 de
celdas 192x208, 1536x1872 px):

- `pets/guante-verde/`: el logo del guante verde animado.
- `pets/angel-gaitan/`: avatar ilustrado de Ángel Gaitán con sus guantes verdes.

## Cuando el usuario pida instalar la mascota

1. Si no estás dentro del repo, clónalo:
   `gh repo clone armandofcom/claude-pets-angel && cd claude-pets-angel`
2. Instala:
   - Si nombra una (el guante o Ángel), solo esa: `./install.sh guante-verde` o `./install.sh angel-gaitan`.
   - Si no dice cuál, las dos: `./install.sh`. Luego podrá cambiar entre ellas en Petdex sin reinstalar.
   El script copia `pet.json` y `spritesheet.webp` a `~/.petdex/pets/<id>/` (Petdex Desktop) y
   `~/.codex/pets/<id>/` (Codex y OpenPets).
3. Comprueba que existen los dos archivos en ambos destinos (`ls -la`).
4. Explica al usuario el último paso, que es suyo y no tuyo:
   descargar Petdex Desktop desde https://petdex.dev/download, abrirlo, pulsar Cmd+, sobre la mascota,
   elegir la mascota en **Pets** y conectar **Claude Code** en **Agents**.
   No descargues ni instales la app sin que el usuario lo confirme.

Alternativa: OpenPets (https://github.com/OpenPetsHQ/openpets) también lee `~/.codex/pets/`.

## Desinstalar

`./install.sh --desinstalar` (todas) o `./install.sh --desinstalar <id>`.

## Regenerar los atlas

```sh
python3 -m venv .venv && .venv/bin/pip install pillow numpy scipy
# Guante Verde, desde el logo
.venv/bin/python tools/generar_atlas.py --logo tools/guante-verde-logo.webp --salida ./salida-guante
# Ángel Gaitán, desde las tiras generadas
.venv/bin/python tools/procesar_tiras.py --tiras fuentes/angel-gaitan --salida ./salida-angel
```

Copia el `spritesheet.webp` resultante a `pets/<id>/`. Ambos scripts salen con código 1 si algún
frame se sale de su celda.

## Reglas

- El guante es el logo de Ángel Gaitán y el avatar reproduce su imagen. No los publiques en la
  galería pública de Petdex (`petdex submit`) ni en otro sitio sin permiso expreso del usuario.
- No cambies el orden de las filas del atlas: idle, running-right, running-left, waving,
  jumping, failed, waiting, running, review.
