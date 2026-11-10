#!/usr/bin/env bash
# Installe pyvision : dépendances dans un venv isolé + commande ~/.local/bin/pyvision
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"
BIN="$HOME/.local/bin"
PY="${PYTHON:-python3}"
DEPS=(flake8 mypy rich pydantic python-dotenv)

say() { printf '\033[1;36m[pyvision]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[pyvision]\033[0m %s\n' "$*" >&2; exit 1; }

command -v "$PY" >/dev/null 2>&1 || die "python3 introuvable."
"$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' \
    || die "Python 3.10 ou plus est nécessaire ($("$PY" --version))."

MANAGED=$("$PY" -c 'import sysconfig, os; print(int(os.path.exists(os.path.join(sysconfig.get_paths()["stdlib"], "EXTERNALLY-MANAGED"))))')

RUNNER=""
if [ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV" >/dev/null 2>&1; then
    say "Environnement isolé : $VENV"
    "$VENV/bin/python" -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
    "$VENV/bin/python" -m pip install --quiet --upgrade "${DEPS[@]}" \
        || die "Échec de l'installation des dépendances (réseau ?)."
    RUNNER="$VENV/bin/python"
elif command -v virtualenv >/dev/null 2>&1 && virtualenv -q -p "$PY" "$VENV"; then
    say "Environnement isolé (virtualenv) : $VENV"
    "$VENV/bin/python" -m pip install --quiet --upgrade "${DEPS[@]}"
    RUNNER="$VENV/bin/python"
elif [ "$MANAGED" = "0" ]; then
    say "venv indisponible : installation avec pip --user"
    "$PY" -m pip install --quiet --user --upgrade "${DEPS[@]}"
    RUNNER="$(command -v "$PY")"
else
    die "Python est « externally managed » et le module venv est absent.
Installez-le (ex. : sudo apt install python3-venv) puis relancez ./install.sh"
fi

mkdir -p "$BIN"
cat > "$BIN/pyvision" <<EOF
#!/usr/bin/env bash
exec "$RUNNER" "$DIR/pyvision.py" "\$@"
EOF
chmod +x "$BIN/pyvision" "$DIR/install.sh"
say "Commande installée : $BIN/pyvision"

case ":$PATH:" in
    *":$BIN:"*) ;;
    *)
        for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
            if [ -f "$rc" ] && ! grep -q 'pyvision: PATH' "$rc"; then
                printf '\nexport PATH="$HOME/.local/bin:$PATH"  # pyvision: PATH\n' >> "$rc"
                say "PATH mis à jour dans $rc"
            fi
        done
        say "Ouvrez un nouveau terminal (ou: export PATH=\"\$HOME/.local/bin:\$PATH\")."
        ;;
esac
say "Terminé. Placez-vous à la racine d'un module et tapez : pyvision"
