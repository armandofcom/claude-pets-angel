# Mascotas de Ángel Gaitán

Dos mascotas animadas de escritorio para [Petdex Desktop](https://petdex.dev), Codex y
[OpenPets](https://github.com/OpenPetsHQ/openpets). Reaccionan a lo que hace Claude Code.
Instala una o las dos y elige cuál ver en Petdex.

| Guante Verde | Ángel Gaitán |
| --- | --- |
| ![Guante Verde](preview/guante-verde/idle.gif) | ![Ángel Gaitán](preview/angel-gaitan/idle.gif) |
| El logo del guante. Salta con el pulgar arriba y gira a pulgar abajo si algo falla. | Avatar de Ángel con sus guantes verdes. Saluda, salta con el pulgar arriba y se lleva la mano a la cara si algo falla. |

## Instalar

```sh
gh repo clone armandofcom/claude-pets-angel
cd claude-pets-angel
./install.sh                  # las dos
./install.sh angel-gaitan     # solo el avatar
./install.sh guante-verde     # solo el guante
```

Después:

1. Descarga [Petdex Desktop](https://petdex.dev/download) y ábrelo.
2. Pon el ratón sobre la mascota y pulsa <kbd>Cmd</kbd>+<kbd>,</kbd>.
3. En **Pets** elige **Guante Verde** o **Ángel Gaitán**.
4. En **Agents** conecta **Claude Code**.

Para quitarlas: `./install.sh --desinstalar` (todas) o `./install.sh --desinstalar angel-gaitan`.

### Con Claude Code

Abre Claude Code en cualquier carpeta y pídele:

> Instala la mascota de https://github.com/armandofcom/claude-pets-angel siguiendo su CLAUDE.md

Claude clonará el repo, ejecutará `install.sh` y te dirá el paso final en Petdex Desktop.

## Animaciones

| Estado | Cuándo sale | Guante Verde | Ángel Gaitán |
| --- | --- | --- | --- |
| idle | Sin actividad | Respira y se balancea | Brazos cruzados, respira y parpadea |
| running-right / left | Arrastras la mascota | Saltitos inclinado | Trota hacia ese lado |
| waving | Saludo o aviso | Se mece | Saluda con el guante |
| jumping | Tarea terminada bien | Salta | Salta con el pulgar arriba |
| failed | Algo falló | Gira a pulgar abajo y pierde color | Se lleva la mano a la cara |
| waiting | Claude espera tu permiso | Toquecitos hacia delante | Mano abierta, «¿te toca?» |
| running | Claude ejecuta o edita | Vibra con energía | Se ajusta los guantes y flexiona los dedos |
| review | Claude piensa o revisa | Se inclina despacio | Mano en la barbilla |

Hojas completas: [guante](preview/guante-verde/contact-sheet.png) · [Ángel](preview/angel-gaitan/contact-sheet.png).

## Formato y cómo se hicieron

- Cada mascota es `pets/<id>/pet.json` + `pets/<id>/spritesheet.webp`: atlas 8x9 de celdas 192x208
  (1536x1872 px), el formato de Codex que también aceptan Petdex y OpenPets.
- Las dos pasan `validate_atlas.py` de la skill `hatch-pet` de Codex sin errores ni avisos.
- **Guante Verde:** `tools/generar_atlas.py` anima el logo real (`tools/guante-verde-logo.webp`).
- **Ángel Gaitán:** ilustración generada con IA en Higgsfield (GPT Image 2) a partir de fotos públicas
  de su web e Instagram. Las tiras originales están en `fuentes/angel-gaitan/` y
  `tools/procesar_tiras.py` las recorta, iguala tamaño y suelo, y monta el atlas.

## Derechos

El guante verde es el logo de Ángel Gaitán y el avatar reproduce su imagen. No se pueden
redistribuir ni subir a galerías públicas (por ejemplo `petdex submit`) sin su permiso.
Los scripts de `tools/` se pueden reutilizar libremente.
