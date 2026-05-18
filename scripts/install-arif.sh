#!/usr/bin/env bash
# Install the `arif` command onto PATH (/usr/local/bin or ~/bin).
set -euo pipefail

ARIF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARIF_BIN="$ARIF_ROOT/scripts/arif"

chmod +x "$ARIF_BIN"

install_to() {
  local dest_dir=$1
  mkdir -p "$dest_dir"
  ln -sf "$ARIF_BIN" "$dest_dir/arif"
  echo "Linked: $dest_dir/arif -> $ARIF_BIN"
}

if [[ -d /usr/local/bin ]]; then
  if install_to /usr/local/bin 2>/dev/null; then
    :
  else
    echo "Need sudo to install to /usr/local/bin..."
    sudo mkdir -p /usr/local/bin
    sudo ln -sf "$ARIF_BIN" /usr/local/bin/arif
    echo "Linked: /usr/local/bin/arif -> $ARIF_BIN"
  fi
else
  install_to "$HOME/bin"
  if ! grep -q 'export PATH="$HOME/bin:$PATH"' "$HOME/.bashrc" 2>/dev/null; then
    echo 'export PATH="$HOME/bin:$PATH"' >>"$HOME/.bashrc"
    echo 'Added $HOME/bin to PATH in ~/.bashrc (run: source ~/.bashrc)'
  fi
fi

if command -v arif &>/dev/null; then
  echo "OK: $(command -v arif)"
  echo "Run: arif"
else
  echo "Install done. Open a new terminal, or run:"
  echo "  source ~/.bashrc"
  echo "  arif"
  echo ""
  echo "Or run directly without installing:"
  echo "  bash $ARIF_BIN"
fi
