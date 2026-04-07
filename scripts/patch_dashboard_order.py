"""
Réordonner les vignettes du dashboard professeur.
Ordre désiré :
  Ligne 1 : Classes, Élèves, Thèmes, PFMP
  Ligne 2 : TàF, Portfolio, Évaluations, Ateliers
  Ligne 3 : TàC, Archives, Statistiques, Assistant
"""
import re
import sys

TMPL = r'core/templates/core/dashboard_professeur.html'

with open(TMPL, encoding='utf-8') as f:
    src = f.read()

# ── ancres pour chaque tuile ──────────────────────────────────────────────────
ANCHORS = {
    'classes':      '<!-- Gestion Classes -->',
    'eleves':       '<!-- Gestion Élèves -->',
    'themes':       '<!-- Gestion Thèmes -->',
    'taf':          '<!-- Travail à Faire -->',
    'pfmp':         '<!-- Gestion PFMP -->',
    'portfolio':    '<!-- Portfolio BAC Pro -->',
    'ateliers':     '<!-- Gestion Ateliers -->',
    'tac':          '<!-- Travaux à Corriger -->',
    'evaluations':  '<!-- Évaluations -->',
    'archives':     '<!-- Archives -->',
    'stats':        '<!-- Statistiques -->',
    'assistant':    '<!-- Assistant IA -->',
}

# Ordre des ancres dans le HTML actuel (déduites de la lecture)
CURRENT_ORDER = ['classes','eleves','themes','taf','pfmp','portfolio','ateliers','tac','evaluations','archives','stats','assistant']
NEW_ORDER     = ['classes','eleves','themes','pfmp','taf','portfolio','evaluations','ateliers','tac','archives','stats','assistant']

# ── extraire chaque bloc entre son ancre et la suivante ──────────────────────
def split_blocks(text, keys, anchors):
    """
    Retourne un dict {key: '<bloc html>'}
    Chaque bloc commence à son ancre et s'arrête juste avant la suivante.
    """
    positions = []
    for key in keys:
        anchor = anchors[key]
        pos = text.find(anchor)
        if pos == -1:
            print(f"ERREUR: ancre introuvable pour {key!r}: {anchor!r}")
            sys.exit(1)
        positions.append((pos, key))
    positions.sort()

    blocks = {}
    for i, (pos, key) in enumerate(positions):
        if i + 1 < len(positions):
            end = positions[i+1][0]
        else:
            end = len(text)
        blocks[key] = text[pos:end]

    return blocks

# ── localiser la section grid ─────────────────────────────────────────────────
GRID_START_MARKER = ANCHORS['classes']
# La section se termine juste avant la ligne "    </div>\n\n{% endblock %}"
GRID_END_MARKER = '\n    </div>\n\n{% endblock %}'

gs = src.find(GRID_START_MARKER)
ge = src.find(GRID_END_MARKER)
if gs == -1 or ge == -1:
    print("ERREUR: impossible de localiser la section grid")
    sys.exit(1)

grid_section = src[gs:ge]
blocks = split_blocks(grid_section, CURRENT_ORDER, ANCHORS)

# ── construire la nouvelle section grid ──────────────────────────────────────
new_grid = ''
for key in NEW_ORDER:
    new_grid += blocks[key]

new_src = src[:gs] + new_grid + src[ge:]

with open(TMPL, 'w', encoding='utf-8') as f:
    f.write(new_src)

print("OK - dashboard réordonné")
print("Nouvel ordre:")
for i, k in enumerate(NEW_ORDER, 1):
    row = (i - 1) // 4 + 1
    col = (i - 1) % 4 + 1
    print(f"  L{row}C{col}: {k}")
