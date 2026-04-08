"""
Patch dashboard_eleve.html:
1. Communication → dans la grille en 4ème colonne (même ligne qu'Ateliers/Cours/A faire)
2. Mes rendus → reste dans la grille mais en 2ème ligne (seul) = pleine largeur
3. grid-4-cols: align-items: start → align-items: stretch
4. Supprimer la section Évaluations
"""

FILE = r'core/templates/core/dashboard_eleve.html'

with open(FILE, encoding='utf-8') as f:
    src = f.read()

# ─── 1. align-items: start → align-items: stretch ──────────────────────────
src = src.replace(
    '        align-items: start;\n    }',
    '        align-items: stretch;\n    }'
)

# ─── 2. Supprimer le bloc Communication standalone (pleine largeur) ───────────
BLOC_COMM = '''    <!-- VIGNETTE COMMUNICATION (pleine largeur) -->
    <a href="{% url 'core:communication_eleve' %}"
       class="section-card"
       style="border-left:5px solid #4a7fc1;text-decoration:none;
              display:block;cursor:pointer;transition:all 0.2s;margin-top:0;">
        <div class="card-header">
            <svg viewBox="0 0 24 24" stroke="#4a7fc1" stroke-width="2"
                 fill="none" style="width:24px;height:24px;flex-shrink:0;">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <h2 style="color:#4a7fc1;margin:0;">Communication</h2>
        </div>
        <p style="color:#6c757d;font-size:0.9rem;margin:0;">
            Envoyer un message ou une photo annotée au professeur
        </p>
    </a>'''

src = src.replace(BLOC_COMM, '')

# ─── 3. Insérer Communication dans la grille AVANT Mes rendus ─────────────────
ANCHOR_RENDUS = '''        <!-- MES RENDUS -->'''
COMM_IN_GRID = '''        <!-- COMMUNICATION -->
        <a href="{% url 'core:communication_eleve' %}" class="section-card"
           style="border-left:5px solid #4a7fc1;text-decoration:none;cursor:pointer;transition:all 0.2s;">
            <div class="card-header">
                <svg viewBox="0 0 24 24" stroke="#4a7fc1" stroke-width="2"
                     fill="none" style="width:24px;height:24px;flex-shrink:0;stroke-linecap:round;stroke-linejoin:round;">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <h2 style="color:#4a7fc1;margin:0;">Communication</h2>
            </div>
            <p style="color:#6c757d;font-size:0.9rem;margin:0;">
                Envoyer un message ou une photo annotée au professeur
            </p>
        </a>

        <!-- MES RENDUS -->'''

src = src.replace(ANCHOR_RENDUS, COMM_IN_GRID, 1)

# ─── 4. Mes rendus: grid-column span pour occuper toute la 2ème ligne ─────────
# On lui ajoute un style grid-column: 1 / -1 pour qu'il s'étale sur toute la largeur
OLD_RENDUS_DIV = '        <!-- MES RENDUS -->\n        <div class="section-card rendus">'
NEW_RENDUS_DIV = '        <!-- MES RENDUS -->\n        <div class="section-card rendus" style="grid-column: 1 / -1;">'
src = src.replace(OLD_RENDUS_DIV, NEW_RENDUS_DIV, 1)

# ─── 5. Supprimer la section Évaluations ──────────────────────────────────────
# La section commence par "<!-- ═══ 5. MES ÉVALUATIONS ═══ -->"
# et se termine avant le <script>
idx_start = src.find('    <!-- ═══ 5. MES ÉVALUATIONS ═══ -->')
idx_end   = src.find('\n<script>', idx_start)
if idx_start != -1 and idx_end != -1:
    src = src[:idx_start] + src[idx_end:]
    print("Section évaluations supprimée")
else:
    print("ERREUR: section évaluations non trouvée")
    print("idx_start:", idx_start, "idx_end:", idx_end)

# ─── Sauvegarde ───────────────────────────────────────────────────────────────
with open(FILE, 'w', encoding='utf-8') as f:
    f.write(src)

print("OK - patch appliqué")

# Vérifications
checks = [
    ('align-items: stretch', True, 'align-items stretch manquant'),
    ('core:communication_eleve', True, 'lien communication manquant'),
    ('VIGNETTE COMMUNICATION (pleine largeur)', False,  'bloc standalone toujours présent'),
    ('mes_evaluations', False, 'évaluations toujours présentes'),
    ('grid-column: 1 / -1', True, 'mes rendus span manquant'),
]
with open(FILE, encoding='utf-8') as f:
    content = f.read()

all_ok = True
for text, should_exist, message in checks:
    exists = text in content
    if exists != should_exist:
        print(f'  ERREUR: {message}')
        all_ok = False
    else:
        status = 'OK' if should_exist else 'supprimé'
        print(f'  [{status}]  {text}')
if all_ok:
    print("Toutes les vérifications OK")
