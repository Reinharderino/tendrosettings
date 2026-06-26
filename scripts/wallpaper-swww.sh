#!/usr/bin/env bash
# wallpaper-swww.sh — aplicador de wallpaper agnóstico al archivo, vía swww/awww.
#
# Lo invoca el módulo de ajustes (hypr-ajustes) para los monitores marcados
# "animated" en wallpaper.json. hyprpaper sigue manejando los estáticos; swww
# solo toca los outputs que se le pasan, así no se pisan entre sí.
#
# Es agnóstico al "papel" (recibe cualquier ruta por parámetro) y al binario:
# usa swww o su fork drop-in awww, el que esté instalado.
set -euo pipefail

PROG=${0##*/}

die() { printf '%s: %s\n' "$PROG" "$*" >&2; exit 1; }

usage() {
    cat <<EOF
Uso: $PROG [opciones] <imagen>

Aplica <imagen> (png/jpg/gif/...) como wallpaper vía swww. Arranca el daemon si
hace falta. Pensado para ser llamado por hypr-ajustes, pero sirve a mano.

Opciones:
  -o, --output OUTPUT      Monitor destino (p.ej. DP-1). Por defecto: todos.
  -f, --fit MODE           cover | contain | stretch | none  (def: cover)
  -t, --transition TYPE    Transición swww, o 'none'         (def: fade)
      --duration SEG       Duración de la transición         (def: 1)
      --fps FPS            FPS de la transición              (def: 60)
  -h, --help               Esta ayuda.

Códigos de salida: 0 ok · 1 error de uso/validación · 2 swww no disponible.
EOF
}

OUTPUT=""
FIT="cover"
TRANSITION="fade"
DURATION="1"
FPS="60"
IMAGE=""

while [ $# -gt 0 ]; do
    case "$1" in
        -o|--output)     OUTPUT=${2:?falta valor para $1}; shift 2;;
        -f|--fit)        FIT=${2:?falta valor para $1}; shift 2;;
        -t|--transition) TRANSITION=${2:?falta valor para $1}; shift 2;;
        --duration)      DURATION=${2:?falta valor para $1}; shift 2;;
        --fps)           FPS=${2:?falta valor para $1}; shift 2;;
        -h|--help)       usage; exit 0;;
        --)              shift; IMAGE=${1:-}; break;;
        -*)              die "opción desconocida: $1 (ver --help)";;
        *)               IMAGE=$1; shift;;
    esac
done

[ -n "$IMAGE" ] || { usage >&2; die "falta la ruta de la imagen"; }

# Expandir ~ y resolver a ruta absoluta (wallpaper.json mezcla ~ y rutas absolutas).
case "$IMAGE" in
    "~")   IMAGE=$HOME;;
    "~/"*) IMAGE=$HOME/${IMAGE#"~/"};;
esac
IMAGE=$(readlink -f -- "$IMAGE") || die "no se pudo resolver la ruta"
[ -f "$IMAGE" ] || die "no existe el archivo: $IMAGE"

# Mapear fit_mode (vocabulario de hypr-ajustes) → --resize {no,crop,fit,stretch}.
case "$FIT" in
    cover)   RESIZE="crop";;
    contain) RESIZE="fit";;
    stretch) RESIZE="stretch";;
    none)    RESIZE="no";;
    *)       die "fit inválido: $FIT (cover|contain|stretch|none)";;
esac

# Detectar el binario: swww o su fork drop-in awww (misma CLI).
BIN=""
for cand in swww awww; do
    if command -v "$cand" >/dev/null 2>&1; then BIN=$cand; break; fi
done
[ -n "$BIN" ] \
    || { printf '%s: ni swww ni awww instalados (paru -S swww)\n' "$PROG" >&2; exit 2; }

# Asegurar el daemon (<bin>-daemon; fallback a '<bin> init' en versiones viejas).
if ! "$BIN" query >/dev/null 2>&1; then
    if command -v "${BIN}-daemon" >/dev/null 2>&1; then
        "${BIN}-daemon" >/dev/null 2>&1 &
    else
        "$BIN" init >/dev/null 2>&1 &
    fi
    # Esperar a que el socket responda (máx ~3s) antes de mandar la imagen.
    for _ in $(seq 1 30); do
        "$BIN" query >/dev/null 2>&1 && break
        sleep 0.1
    done
    "$BIN" query >/dev/null 2>&1 \
        || { printf '%s: %s-daemon no respondió\n' "$PROG" "$BIN" >&2; exit 2; }
fi

args=(img "$IMAGE" --resize "$RESIZE")
[ -n "$OUTPUT" ] && args+=(--outputs "$OUTPUT")
if [ "$TRANSITION" = "none" ]; then
    args+=(--transition-type none)
else
    args+=(--transition-type "$TRANSITION" \
           --transition-duration "$DURATION" \
           --transition-fps "$FPS")
fi

exec "$BIN" "${args[@]}"
