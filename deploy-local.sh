#!/bin/zsh
# textext-improved: install this checkout over the TexText extension in the user's Inkscape.
# - Backs up the installed folder to build/installed-backup-<timestamp>/ (outside the extensions
#   folder, so Inkscape never loads two copies).
# - Keeps the user's own default_packages.tex and LATEX_OPTIONS.
# - Never deletes files from the installed folder.
# Python changes take effect the next time the extension runs; no Inkscape restart needed
# unless textext.inx changed.
set -euo pipefail
repo="${0:A:h}"
dest="$HOME/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/textext"
[[ -d "$dest" ]] || { echo "Installed TexText not found at: $dest" >&2; exit 1; }

stamp=$(date +%Y%m%d-%H%M%S)
backup="$repo/build/installed-backup-$stamp"
mkdir -p "$repo/build"
cp -Rp "$dest" "$backup"
echo "Backup: $backup"

inx_changed=0
cmp -s "$repo/textext/textext.inx" "$dest/textext.inx" || inx_changed=1

rsync -a --exclude '__pycache__/' --exclude 'default_packages.tex' --exclude 'LATEX_OPTIONS' \
  "$repo/textext/" "$dest/"
rm -rf "$dest/__pycache__"

echo "Installed TexText $(cat "$dest/VERSION")"
(( inx_changed )) && echo "textext.inx changed: restart Inkscape." || echo "No Inkscape restart needed."
