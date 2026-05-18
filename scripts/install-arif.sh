#!/usr/bin/env bash
# Install the `arif` command onto PATH (~/bin + /usr/local/bin).
set -euo pipefail

ARIF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARIF_BIN="$ARIF_ROOT/scripts/arif"
PATH_MARKER='# arif launcher'
PATH_LINE='export PATH="$HOME/bin:/usr/local/bin:$PATH"'

chmod +x "$ARIF_BIN"
[[ -f "$ARIF_ROOT/arif" ]] && chmod +x "$ARIF_ROOT/arif"

mkdir -p "$HOME/bin"
ln -sf "$ARIF_BIN" "$HOME/bin/arif"
echo "Linked: $HOME/bin/arif -> $ARIF_BIN"

if [[ -d /usr/local/bin ]]; then
  if sudo ln -sf "$ARIF_BIN" /usr/local/bin/arif 2>/dev/null; then
    echo "Linked: /usr/local/bin/arif -> $ARIF_BIN"
  else
    echo "WARN: could not link /usr/local/bin/arif (sudo failed) — using ~/bin only"
  fi
fi

add_path_to_file() {
  local f=$1
  [[ -f "$f" ]] || touch "$f"
  if grep -qF "$PATH_MARKER" "$f" 2>/dev/null; then
    return 0
  fi
  {
    echo ""
    echo "$PATH_MARKER"
    echo "$PATH_LINE"
    echo "export ARIF_ROOT=\"$ARIF_ROOT\""
  } >>"$f"
  echo "Updated: $f"
}

add_path_to_file "$HOME/.bashrc"
add_path_to_file "$HOME/.profile"

if [[ -w /etc/profile.d ]]; then
  printf '%s\n%s\nexport ARIF_ROOT="%s"\n' "$PATH_MARKER" "$PATH_LINE" "$ARIF_ROOT" \
    | sudo tee /etc/profile.d/arif.sh >/dev/null && echo "Updated: /etc/profile.d/arif.sh"
fi

export PATH="$HOME/bin:/usr/local/bin:$PATH"

echo ""
if command -v arif &>/dev/null; then
  echo "OK: $(command -v arif)"
  echo ""
  echo "Start Arif now:"
  echo "  arif"
else
  echo "Install finished but 'arif' not visible in this shell yet."
  echo "Run:"
  echo "  source ~/.bashrc"
  echo "  arif"
  echo ""
  echo "Or without installing:"
  echo "  bash $ARIF_BIN"
fi
