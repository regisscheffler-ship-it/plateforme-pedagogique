"""
Patch fiche_portfolio_eleve_create.html:
1. Supprimer emojis (unicode + HTML entities)
2. Supprimer champ type_evaluation
3. CSS: ajouter .preview-remove
4. JS: accumulation photos + bouton supprimer
"""
import re

FILE = r'core/templates/core/fiche_portfolio_eleve_create.html'

with open(FILE, encoding='utf-8') as f:
    src = f.read()

# ─── 1. info-banner: enlever ℹ️ ────────────────────────────────────────────
src = src.replace(
    '    ℹ️ Vous créez une nouvelle fiche de suivi.',
    '    Vous créez une nouvelle fiche de suivi.'
)

# ─── 2. Titres des zones élève : supprimer les emojis + espace ───────────────
src = src.replace(
    '<div class="eleve-zone-title">✍️ Description de la situation de travail</div>',
    '<div class="eleve-zone-title">Description de la situation de travail</div>'
)
src = src.replace(
    '<div class="eleve-zone-title">🔍 Observation de l\'environnement professionnel</div>',
    '<div class="eleve-zone-title">Observation de l\'environnement professionnel</div>'
)
src = src.replace(
    '<div class="eleve-zone-title">💡 Problématique identifiée</div>',
    '<div class="eleve-zone-title">Problématique identifiée</div>'
)
# HTML entities
src = src.replace(
    '<div class="eleve-zone-title" style="color:#1d4ed8;">&#128214; Pour cela, je dois connaître</div>',
    '<div class="eleve-zone-title" style="color:#1d4ed8;">Pour cela, je dois connaître</div>'
)
src = src.replace(
    '<div class="eleve-zone-title">&#128295; Je dispose (matériels, matériaux)</div>',
    '<div class="eleve-zone-title">Je dispose (matériels, matériaux)</div>'
)
src = src.replace(
    '<div class="eleve-zone-title" style="color:#065f46;">&#128203; Consigne de l\'entreprise</div>',
    '<div class="eleve-zone-title" style="color:#065f46;">Consigne de l\'entreprise</div>'
)
src = src.replace(
    '<div class="eleve-zone-title" style="color:#b91c1c;">&#9888;&#65039; Risques et EPI</div>',
    '<div class="eleve-zone-title" style="color:#b91c1c;">Risques et EPI</div>'
)

# ─── 3. Supprimer type_evaluation : row-2 → single full-width div ────────────
OLD_ROW2 = '''            <div class="row-2">
                <div>
                    <label class="form-label" for="id_titre">Titre de la fiche <span class="required">*</span></label>
                    <input type="text" name="titre" id="id_titre" class="form-input"
                           placeholder="Ex : Pose d\'un revêtement mural — Stage chez Dupont…"
                           value="{{ request.POST.titre|default:\'\' }}" required>
                </div>
                <div>
                    <label class="form-label" for="id_type">Type d\'évaluation</label>
                    <select name="type_evaluation" id="id_type" class="form-select">
                        <option value="formative" {% if request.POST.type_evaluation == \'formative\' or not request.POST.type_evaluation %}selected{% endif %}>Formative</option>
                        <option value="sommative" {% if request.POST.type_evaluation == \'sommative\' %}selected{% endif %}>Sommative</option>
                        <option value="certificative" {% if request.POST.type_evaluation == \'certificative\' %}selected{% endif %}>Certificative</option>
                    </select>
                </div>
            </div>'''

NEW_ROW = '''            <div>
                <label class="form-label" for="id_titre">Titre de la fiche <span class="required">*</span></label>
                <input type="text" name="titre" id="id_titre" class="form-input"
                       placeholder="Ex : Pose d\'un revêtement mural — Stage chez Dupont…"
                       value="{{ request.POST.titre|default:\'\' }}" required>
            </div>'''

src = src.replace(OLD_ROW2, NEW_ROW)

# ─── 4. CSS: ajouter .preview-remove après .preview-name ─────────────────────
OLD_CSS = '    .preview-item .preview-name { padding: 4px 6px; font-size: 0.68rem; color: #64748b; background: white; border-top: 1px solid #e2e8f0; }'
NEW_CSS = '''    .preview-item .preview-name { padding: 4px 6px; font-size: 0.68rem; color: #64748b; background: white; border-top: 1px solid #e2e8f0; }
    .preview-remove {
        position: absolute; top: 4px; right: 4px;
        background: rgba(220,38,38,0.85); color: white;
        border: none; border-radius: 50%; width: 22px; height: 22px;
        font-size: 1rem; font-weight: 700; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        padding: 0; line-height: 1;
    }
    .preview-remove:hover { background: #dc2626; }'''

src = src.replace(OLD_CSS, NEW_CSS)

# ─── 5. Section PHOTOS: remplacer onchange + section heading ─────────────────
OLD_PHOTOS = '''        <!-- PHOTOS -->
        <div class="info-section" style="border-bottom:none;">
            <div class="section-heading">
                Photos justificatives (8 max)
                <span class="tag-eleve">Élève</span>
            </div>
            <div id="preview-grid" class="photos-preview-grid"></div>
            <label class="photo-upload-zone" for="id_photos">
                <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <rect x="3" y="3" width="18" height="18" rx="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <polyline points="21 15 16 10 5 21"/>
                </svg>
                <div style="font-weight:600;">Cliquez pour ajouter des photos</div>
                <div style="font-size:0.78rem;margin-top:2px;">JPEG ou PNG — 8 maximum, 5 Mo max par photo</div>
            </label>
            <input type="file" id="id_photos" name="photos" multiple accept="image/*"
                   style="display:none;" onchange="previewFiles(this)">
        </div>'''

NEW_PHOTOS = '''        <!-- PHOTOS -->
        <div class="info-section" style="border-bottom:none;">
            <div class="section-heading">
                Photos justificatives (<span id="count-photos">0</span>/8)
                <span class="tag-eleve">Élève</span>
            </div>
            <div id="preview-grid" class="photos-preview-grid"></div>
            <label class="photo-upload-zone" for="id_photos" id="upload-zone">
                <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <rect x="3" y="3" width="18" height="18" rx="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <polyline points="21 15 16 10 5 21"/>
                </svg>
                <div style="font-weight:600;">Cliquez pour ajouter des photos</div>
                <div style="font-size:0.78rem;margin-top:2px;">JPEG ou PNG — 8 maximum, 5 Mo max par photo</div>
            </label>
            <input type="file" id="id_photos" name="photos" multiple accept="image/*"
                   style="display:none;" onchange="addFiles(this)">
        </div>'''

src = src.replace(OLD_PHOTOS, NEW_PHOTOS)

# ─── 6. JS: remplacer le script entier ───────────────────────────────────────
OLD_JS = '''<script>
function previewFiles(input) {
    const max = 8;
    if (input.files.length > max) {
        alert('Vous ne pouvez pas dépasser ' + max + ' photos.');
        input.value = '';
        return;
    }
    const grid = document.getElementById('preview-grid');
    grid.innerHTML = '';
    Array.from(input.files).forEach(file => {
        const reader = new FileReader();
        reader.onload = function(e) {
            const div = document.createElement('div');
            div.className = 'preview-item';
            div.innerHTML = '<img src="' + e.target.result + '" alt=""><div class="preview-name">' + file.name.slice(-18) + '</div>';
            grid.appendChild(div);
        };
        reader.readAsDataURL(file);
    });
}
</script>'''

NEW_JS = '''<script>
let pendingFiles = [];

function addFiles(input) {
    const newFiles = Array.from(input.files);
    const remaining = 8 - pendingFiles.length;
    if (newFiles.length > remaining) {
        alert('Vous ne pouvez ajouter que ' + remaining + ' photo(s) supplémentaire(s) (max 8 au total).');
        input.value = '';
        return;
    }
    newFiles.forEach(f => pendingFiles.push(f));
    input.value = ''; // reset pour permettre de resélectionner le même fichier
    syncInput();
    renderPreviews();
}

function removeFile(i) {
    pendingFiles.splice(i, 1);
    syncInput();
    renderPreviews();
}

function syncInput() {
    const dt = new DataTransfer();
    pendingFiles.forEach(f => dt.items.add(f));
    document.getElementById(\'id_photos\').files = dt.files;
    const counter = document.getElementById(\'count-photos\');
    if (counter) counter.textContent = pendingFiles.length;
    const zone = document.getElementById(\'upload-zone\');
    if (zone) zone.style.display = pendingFiles.length >= 8 ? \'none\' : \'\';
}

function renderPreviews() {
    const grid = document.getElementById(\'preview-grid\');
    grid.innerHTML = \'\';
    pendingFiles.forEach((file, i) => {
        const div = document.createElement(\'div\');
        div.className = \'preview-item\';
        grid.appendChild(div);
        const reader = new FileReader();
        reader.onload = function(e) {
            div.innerHTML = \'<img src="\' + e.target.result + \'" alt="">\' +
                \'<button type="button" class="preview-remove" onclick="removeFile(\' + i + \')" title="Supprimer">&times;</button>\' +
                \'<div class="preview-name">\' + file.name.slice(-20) + \'</div>\';
        };
        reader.readAsDataURL(file);
    });
}
</script>'''

src = src.replace(OLD_JS, NEW_JS)

# ─── Sauvegarde ──────────────────────────────────────────────────────────────
with open(FILE, 'w', encoding='utf-8') as f:
    f.write(src)

print("OK - patch appliqué")

# Vérification
checks = [
    ('✍️', False, 'emoji ✍️ toujours présent'),
    ('🔍', False, 'emoji 🔍 toujours présent'),
    ('💡', False, 'emoji 💡 toujours présent'),
    ('ℹ️', False, 'emoji ℹ️ toujours présent'),
    ('&#128214;', False, 'emoji &#128214; toujours présent'),
    ('&#9888;', False, 'emoji &#9888; toujours présent'),
    ('type_evaluation', False, 'type_evaluation toujours présent'),
    ('count-photos', True, 'count-photos manquant'),
    ('pendingFiles', True, 'pendingFiles manquant'),
    ('removeFile', True, 'removeFile manquant'),
    ('preview-remove', True, 'preview-remove manquant'),
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
        status = '✓' if should_exist else '✗ (supprimé)'
        print(f'  {status}  {text}')

if all_ok:
    print("Toutes les vérifications OK")
