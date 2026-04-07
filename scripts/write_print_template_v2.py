"""
Réécriture de fiche_portfolio_print.html :
- Page A4 pleine hauteur : les blocs texte s'étendent pour remplir la page
- Outil de recadrage photo (position X/Y) avant impression
"""
import os

BASE = r"C:\Users\regis\OneDrive - CR HDF\Documents\plateforme_pedagogique v2 Copilote\plateforme-pedagogique"
path = os.path.join(BASE, "core", "templates", "core", "fiche_portfolio_print.html")

# On construit le template en morceaux pour éviter les problèmes de triple-quotes
parts = []

parts.append('{% load static %}\n')
parts.append('<!DOCTYPE html>\n')
parts.append('<html lang="fr">\n')
parts.append('<head>\n')
parts.append('<meta charset="UTF-8">\n')
parts.append('<title>Portfolio \u2014 {{ portfolio.eleve.user.last_name }} {{ portfolio.eleve.user.first_name }}</title>\n')

# ─── STYLES ───────────────────────────────────────────────────────────────────
parts.append("""<style>
/* =================================================================
   RESET & BASE
================================================================= */
@page { size: A4 portrait; margin: 0; }
*, *::before, *::after { box-sizing: border-box; }
* { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
body { font-family: Arial, Helvetica, sans-serif; background: #4b5563; margin: 0; font-size: 11px; }

/* =================================================================
   BARRE D'ACTIONS
================================================================= */
.action-bar {
    background: white; padding: 10px 20px;
    box-shadow: 0 4px 8px rgba(0,0,0,.12);
    position: sticky; top: 0; z-index: 1000;
    display: flex; justify-content: center; align-items: center; gap: 16px;
    border-bottom: 4px solid #d97706; margin-bottom: 20px;
}
.btn {
    padding: 8px 16px; border: none; border-radius: 6px;
    font-size: 13px; font-weight: 600; cursor: pointer;
    display: inline-flex; align-items: center; gap: 6px; text-decoration: none;
}
.btn-back  { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
.btn-back:hover { background: #e5e7eb; }
.btn-print { background: #d97706; color: white; }
.btn-print:hover { background: #b45309; }
.bar-info  { font-size: 0.85rem; color: #6b7280; }

/* =================================================================
   FEUILLES A4 — base commune (couverture + fiches)
================================================================= */
.sheet {
    background: white;
    width: 210mm;
    min-height: 297mm;
    margin: 20px auto;
    padding: 10mm 12mm;
    box-shadow: 0 0 15px rgba(0,0,0,.4);
    display: flex; flex-direction: column;
}

/* La fiche (pas la couverture) doit TOUJOURS remplir toute la hauteur A4 */
.sheet-fiche {
    /* En écran : grandi si le contenu dépasse */
    height: 297mm;
    overflow: visible;
}

@media print {
    body { background: none; }
    .sheet {
        margin: 0; box-shadow: none; padding: 8mm 10mm;
        page-break-after: always;
    }
    .sheet:last-child { page-break-after: avoid; }
    .sheet-fiche { height: 297mm; overflow: hidden; }
    .no-print { display: none !important; }
}

/* =================================================================
   COUVERTURE
================================================================= */
.cover-title {
    font-size: 26px; font-weight: 800; color: #1e293b;
    border-bottom: 4px solid #d97706; padding-bottom: 8px;
    margin-bottom: 14px; text-transform: uppercase; letter-spacing: .04em;
}
.cover-student-box {
    border: 2px solid #d97706; border-radius: 6px;
    padding: 12px 16px; background: #fffbeb; margin-bottom: 16px;
}
.cover-student-box .label { font-size: 9px; font-weight: 700; color: #92400e; text-transform: uppercase; }
.cover-student-box .value { font-size: 17px; font-weight: 800; color: #1e293b; margin-top: 2px; }
.cover-student-box .sub   { font-size: 11px; color: #64748b; margin-top: 2px; }
.cover-stats { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.cover-stat  { flex: 1; min-width: 70px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; text-align: center; }
.cover-stat-value { font-size: 20px; font-weight: 800; color: #d97706; display: block; }
.cover-stat-label { font-size: 9px; color: #94a3b8; text-transform: uppercase; }
.cover-stat.green .cover-stat-value { color: #10b981; }
.cover-fiches-list { margin-top: 12px; }
.cover-fiche-line { display: flex; align-items: center; gap: 8px; padding: 4px 0; border-bottom: 1px solid #f1f5f9; font-size: 10px; }
.cover-fiche-line .num   { font-weight: 700; color: #d97706; min-width: 20px; }
.cover-fiche-line .titre { flex: 1; color: #374151; }
.badge-sm { font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 10px; text-transform: uppercase; letter-spacing: .04em; }
.badge-formative     { background: #dbeafe; color: #1d4ed8; }
.badge-sommative     { background: #fce7f3; color: #9d174d; }
.badge-certificative { background: #f3e8ff; color: #6d28d9; }
.badge-ok   { background: #d1fae5; color: #065f46; }
.badge-wait { background: #fef3c7; color: #92400e; }

/* =================================================================
   FICHE : EN-TÊTE
================================================================= */
.fiche-header {
    display: flex; align-items: flex-start; gap: 10px;
    border-bottom: 3px solid #d97706; padding-bottom: 8px; margin-bottom: 7px;
    flex-shrink: 0;
}
.fiche-header-logo { width: 54px; height: 54px; flex-shrink: 0; object-fit: contain; }
.fiche-header-logo-placeholder {
    width: 54px; height: 54px; flex-shrink: 0;
    background: #fef3c7; border: 2px solid #d97706; border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 700; color: #92400e; text-align: center; line-height: 1.2;
}
.fiche-header-center {
    flex: 1; border: 2px solid #374151; border-radius: 4px;
    padding: 6px 10px; min-height: 48px;
    display: flex; align-items: center;
}
.fiche-header-title { font-size: 13px; font-weight: 800; color: #1e293b; line-height: 1.3; }
.fiche-header-right { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; flex-shrink: 0; }
.fiche-header-eleve { font-size: 9px; color: #64748b; text-align: right; }
.fiche-header-eleve strong { color: #374151; }
.type-row  { display: flex; gap: 8px; align-items: center; margin-top: 3px; }
.type-item { display: flex; align-items: center; gap: 3px; font-size: 9px; color: #374151; }
.type-box  { width: 12px; height: 12px; border: 1.5px solid #374151; border-radius: 2px; display: inline-flex; align-items: center; justify-content: center; font-size: 8px; font-weight: 900; flex-shrink: 0; }
.type-box.checked { background: #1e293b; color: white; }

/* =================================================================
   TABLE UNITÉ / COMPÉTENCES / ACTIVITÉS
================================================================= */
.fiche-table { width: 100%; border-collapse: collapse; font-size: 9.5px; margin-bottom: 6px; flex-shrink: 0; }
.fiche-table th { background: #f1f5f9; color: #374151; font-weight: 700; border: 1.5px solid #94a3b8; padding: 4px 6px; font-size: 9px; text-align: left; text-transform: uppercase; letter-spacing: .04em; }
.fiche-table td { border: 1.5px solid #94a3b8; padding: 5px 6px; vertical-align: top; line-height: 1.4; font-size: 9.5px; color: #374151; }
.fiche-table .col-unite { width: 22%; }
.fiche-table .col-comp  { width: 38%; }
.fiche-table .col-activ { width: 40%; }
.comp-line { display: flex; align-items: baseline; gap: 4px; padding: 1px 0; }
.comp-code { font-size: 9px; font-weight: 700; color: #d97706; white-space: nowrap; }

/* =================================================================
   PHOTOS — section + recadrage
================================================================= */
.photos-section {
    border: 2px solid #f59e0b; border-radius: 4px;
    padding: 5px 7px; margin-bottom: 5px; flex-shrink: 0;
}
.section-label {
    font-size: 9px; font-weight: 700; color: #92400e;
    text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px;
}
.photos-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }

/* Wrapper pour recadrage : overflow:hidden + img object-fit */
.photo-thumb {
    border-radius: 3px; overflow: hidden;
    border: 1px solid #e2e8f0; background: #f8fafc;
    position: relative;
}
.photo-crop-wrap {
    height: 68px; overflow: hidden; position: relative;
}
.photo-crop-wrap img {
    width: 100%; height: 100%;
    object-fit: cover; object-position: 50% 50%;
    display: block;
}
.photo-thumb .caption {
    font-size: 7px; color: #64748b; padding: 2px 4px;
    text-align: center; background: white; border-top: 1px solid #f1f5f9;
    overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
}
.photo-placeholder {
    height: 68px; display: flex; align-items: center; justify-content: center;
    background: #f8fafc; color: #d1d5db; font-size: 9px; color: #94a3b8; font-style: italic;
}

/* Bouton recadrer (no-print, visible au survol) */
.crop-btn {
    position: absolute; top: 3px; left: 3px; z-index: 5;
    background: rgba(217,119,6,.9); color: white; border: none;
    border-radius: 3px; padding: 2px 5px; font-size: 9px; cursor: pointer;
    display: none; align-items: center; gap: 2px; font-weight: 700;
    line-height: 1.2;
}
.photo-thumb:hover .crop-btn { display: flex; }
.crop-btn:hover { background: #b45309; }

/* =================================================================
   BLOCS TEXTE — structure flex pour remplir la page
================================================================= */
/* Zone qui grandit pour remplir toute la hauteur disponible */
.fiche-body {
    flex: 1;
    display: flex; flex-direction: column; gap: 5px;
    overflow: hidden;
}

/* Bloc de base */
.text-bloc {
    border: 2px solid #f59e0b; border-radius: 4px;
    padding: 5px 7px;
    /* Par défaut : taille fixe (utile pour les lignes de texte courtes) */
}
/* Bloc qui grandit verticalement */
.text-bloc.grow {
    flex: 1;
    display: flex; flex-direction: column;
    min-height: 28px;
}
.text-bloc.grow .bloc-body { flex: 1; }

.text-bloc .bloc-title {
    font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .05em; margin-bottom: 3px; flex-shrink: 0;
}
.text-bloc .bloc-body {
    font-size: 9.5px; color: #1e293b; line-height: 1.5;
    white-space: pre-wrap; min-height: 14px;
}
.text-bloc .empty { color: #d1d5db; font-style: italic; font-size: 9px; }

/* Couleurs */
.bloc-orange { border-color: #f59e0b; }
.bloc-orange .bloc-title { color: #92400e; }
.bloc-bleu   { border-color: #3b82f6; }
.bloc-bleu   .bloc-title { color: #1d4ed8; }
.bloc-gris   { border-color: #94a3b8; }
.bloc-gris   .bloc-title { color: #374151; }
.bloc-vert   { border-color: #10b981; }
.bloc-vert   .bloc-title { color: #065f46; }
.bloc-rouge  { border-color: #ef4444; }
.bloc-rouge  .bloc-title { color: #991b1b; }

/* Grille 2 colonnes (utilise flexbox pour que les cellules grandissent) */
.fiche-grid-2 {
    display: flex; gap: 5px; flex: 1;
    min-height: 28px;
}
.fiche-grid-2 > .text-bloc {
    flex: 1;
    display: flex; flex-direction: column;
    margin-bottom: 0;
}
.fiche-grid-2 > .text-bloc .bloc-body { flex: 1; }

/* Validation stamp */
.stamp-validated {
    border: 2px solid #10b981; border-radius: 6px;
    padding: 4px 10px; display: inline-flex; align-items: center; gap: 5px;
    color: #065f46; font-size: 9px; font-weight: 700;
}
.flex-end { display: flex; justify-content: flex-end; }

/* =================================================================
   MODAL DE RECADRAGE (no-print)
================================================================= */
.crop-modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,.65);
    z-index: 9999; display: none;
    align-items: center; justify-content: center;
}
.crop-modal-overlay.open { display: flex; }
.crop-modal-box {
    background: white; border-radius: 12px;
    padding: 20px 24px; width: 380px; max-width: 96vw;
    box-shadow: 0 20px 60px rgba(0,0,0,.4);
}
.crop-modal-title {
    font-size: 14px; font-weight: 700; color: #1e293b;
    margin-bottom: 14px; display: flex; align-items: center; gap: 6px;
}
/* Aperçu du recadrage — même ratio que le thumbnail */
.crop-preview-container {
    width: 100%; height: 130px; overflow: hidden;
    border: 2px solid #d97706; border-radius: 6px;
    margin-bottom: 14px; background: #f1f5f9;
}
.crop-preview-container img {
    width: 100%; height: 100%;
    object-fit: cover; object-position: 50% 50%;
    display: block;
}
.crop-slider-row {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 10px; font-size: 11px; color: #374151;
}
.crop-slider-row label { min-width: 100px; font-weight: 600; flex-shrink: 0; }
.crop-slider-row input[type=range] {
    flex: 1; accent-color: #d97706;
}
.crop-slider-row .val {
    min-width: 28px; font-size: 10px; color: #94a3b8; text-align: right;
}
.crop-modal-actions {
    display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px;
}
.crop-btn-cancel {
    padding: 6px 14px; background: white; color: #64748b;
    border: 1.5px solid #e2e8f0; border-radius: 6px; cursor: pointer;
    font-size: 12px; font-weight: 600;
}
.crop-btn-apply {
    padding: 6px 16px; background: #d97706; color: white;
    border: none; border-radius: 6px; cursor: pointer;
    font-size: 12px; font-weight: 700;
}
.crop-btn-apply:hover { background: #b45309; }
.crop-btn-reset {
    padding: 6px 12px; background: #f1f5f9; color: #374151;
    border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer;
    font-size: 11px; margin-right: auto;
}
</style>
</head>
<body>
""")

# ─── BARRE D'ACTIONS ─────────────────────────────────────────────────────────
parts.append("""
<!-- BARRE D'ACTIONS -->
<div class="no-print action-bar">
    <a href="{% url 'core:portfolio_detail' portfolio.id %}" class="btn btn-back">
        <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>
        Retour au portfolio
    </a>
    <button onclick="window.print()" class="btn btn-print">
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="6 9 6 2 18 2 18 9"></polyline><rect x="6" y="14" width="12" height="8"></rect><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path></svg>
        Imprimer ({{ fiches|length }} fiche{% if fiches|length > 1 %}s{% endif %})
    </button>
    <span class="bar-info">
        {{ portfolio.eleve.user.last_name }} {{ portfolio.eleve.user.first_name }}
        &mdash; {{ portfolio.nb_fiches_validees }}/{{ fiches|length }} valid\u00e9e(s)
    </span>
    <span class="bar-info" style="color:#d97706;font-size:0.78rem;">
        \u2702\ufe0e Survolez une photo puis cliquez <strong>Recadrer</strong> pour ajuster avant impression
    </span>
</div>

<!-- MODAL DE RECADRAGE (no-print) -->
<div class="crop-modal-overlay no-print" id="cropModal">
    <div class="crop-modal-box">
        <div class="crop-modal-title">
            <svg width="16" height="16" fill="none" stroke="#d97706" stroke-width="2" viewBox="0 0 24 24"><polyline points="6 2 6 6 2 6"></polyline><polyline points="18 22 18 18 22 18"></polyline><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            Recadrer la photo
        </div>
        <!-- Aper\u00e7u live du recadrage -->
        <div class="crop-preview-container">
            <img id="cropPreviewImg" src="" alt="Aper\u00e7u">
        </div>
        <!-- Sliders -->
        <div class="crop-slider-row">
            <label>\u2194 Horizontal :</label>
            <input type="range" id="cropX" min="0" max="100" value="50" oninput="updateCropPreview()">
            <span class="val" id="cropXVal">50%</span>
        </div>
        <div class="crop-slider-row">
            <label>\u2195 Vertical :</label>
            <input type="range" id="cropY" min="0" max="100" value="50" oninput="updateCropPreview()">
            <span class="val" id="cropYVal">50%</span>
        </div>
        <div class="crop-modal-actions">
            <button class="crop-btn-reset" onclick="resetCrop()" title="Revenir au centre">&#8635; R\u00e9initialiser</button>
            <button class="crop-btn-cancel" onclick="closeCropModal()">Annuler</button>
            <button class="crop-btn-apply" onclick="applyCrop()">&#10003; Appliquer</button>
        </div>
    </div>
</div>
""")

# ─── COUVERTURE ───────────────────────────────────────────────────────────────
parts.append("""
<!-- ================================================================ -->
<!-- COUVERTURE                                                        -->
<!-- ================================================================ -->
<div class="sheet">
    <div class="cover-title">Portfolio BAC Pro</div>
    <p style="font-size:11px;color:#64748b;margin-bottom:16px;">Document de suivi des activit\u00e9s professionnelles</p>

    <div class="cover-student-box">
        <div class="label">\u00c9l\u00e8ve</div>
        <div class="value">{{ portfolio.eleve.user.last_name|upper }} {{ portfolio.eleve.user.first_name }}</div>
        <div class="sub">
            {% if portfolio.eleve.classe %}{{ portfolio.eleve.classe.nom }}{% endif %}
            {% if portfolio.eleve.classe and portfolio.eleve.classe.niveau %} \u2014 {{ portfolio.eleve.classe.niveau.nom }}{% endif %}
        </div>
    </div>

    <div class="cover-stats">
        <div class="cover-stat">
            <span class="cover-stat-value">{{ fiches|length }}</span>
            <span class="cover-stat-label">Fiche{% if fiches|length > 1 %}s{% endif %}</span>
        </div>
        <div class="cover-stat green">
            <span class="cover-stat-value">{{ portfolio.nb_fiches_validees }}</span>
            <span class="cover-stat-label">Valid\u00e9e{% if portfolio.nb_fiches_validees > 1 %}s{% endif %}</span>
        </div>
        <div class="cover-stat" style="border-color:#fcd34d;">
            <span class="cover-stat-value" style="color:#f59e0b;">{{ portfolio.nb_fiches_remplies }}</span>
            <span class="cover-stat-label">En attente</span>
        </div>
        <div class="cover-stat" style="border-color:#cbd5e1;">
            <span class="cover-stat-value" style="color:#94a3b8;">{{ portfolio.nb_fiches_vides }}</span>
            <span class="cover-stat-label">\u00c0 remplir</span>
        </div>
    </div>

    <div class="cover-fiches-list">
        <div style="font-size:10px;font-weight:700;color:#374151;margin-bottom:6px;text-transform:uppercase;letter-spacing:.05em;">Liste des fiches</div>
        {% for fiche in fiches %}
        <div class="cover-fiche-line">
            <span class="num">{{ forloop.counter }}.</span>
            <span class="titre">{{ fiche.titre }}</span>
            <span class="badge-sm badge-{{ fiche.type_evaluation }}">{{ fiche.get_type_evaluation_display }}</span>
            {% if fiche.validee_par_prof %}
            <span class="badge-sm badge-ok">\u2713 Valid\u00e9e</span>
            {% else %}
            <span class="badge-sm badge-wait">En attente</span>
            {% endif %}
        </div>
        {% empty %}
        <p style="color:#94a3b8;font-style:italic;font-size:10px;">Aucune fiche dans ce portfolio.</p>
        {% endfor %}
    </div>
</div>
""")

# ─── FICHES ──────────────────────────────────────────────────────────────────
parts.append("""
<!-- ================================================================ -->
<!-- UNE PAGE A4 PAR FICHE                                            -->
<!-- ================================================================ -->
{% for fiche in fiches %}
<div class="sheet sheet-fiche">

    <!-- EN-T\u00caTE : Logo | Titre | Type -->
    <div class="fiche-header">
        <img src="{% static 'logoL_LOUCHEUR.jpg' %}" alt="Logo" class="fiche-header-logo"
             onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
        <div class="fiche-header-logo-placeholder" style="display:none;">L.L</div>
        <div class="fiche-header-center">
            <div class="fiche-header-title">{{ fiche.titre }}</div>
        </div>
        <div class="fiche-header-right">
            <div class="fiche-header-eleve">
                <strong>{{ portfolio.eleve.user.last_name|upper }} {{ portfolio.eleve.user.first_name }}</strong><br>
                {% if portfolio.eleve.classe %}{{ portfolio.eleve.classe.nom }}{% endif %}<br>
                {{ fiche.date_creation|date:"d/m/Y" }}
            </div>
            <div class="type-row">
                <div class="type-item">
                    <span class="type-box {% if fiche.type_evaluation == 'formative' %}checked{% endif %}">{% if fiche.type_evaluation == 'formative' %}\u2713{% endif %}</span>
                    Formative
                </div>
                <div class="type-item">
                    <span class="type-box {% if fiche.type_evaluation == 'sommative' %}checked{% endif %}">{% if fiche.type_evaluation == 'sommative' %}\u2713{% endif %}</span>
                    Sommative
                </div>
                <div class="type-item">
                    <span class="type-box {% if fiche.type_evaluation == 'certificative' %}checked{% endif %}">{% if fiche.type_evaluation == 'certificative' %}\u2713{% endif %}</span>
                    Certificative
                </div>
            </div>
        </div>
    </div>

    <!-- TABLEAU : Unit\u00e9 | Comp\u00e9tences | Activit\u00e9s -->
    <table class="fiche-table">
        <thead>
            <tr>
                <th class="col-unite">Unit\u00e9 d\u2019\u00e9valuation</th>
                <th class="col-comp">Comp\u00e9tences \u00e9valu\u00e9es</th>
                <th class="col-activ">Activit\u00e9s Professionnelles</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="col-unite">{{ fiche.unite_evaluation|default:"" }}</td>
                <td class="col-comp">
                    {% for c in fiche.competences.all %}
                    <div class="comp-line">
                        <span class="comp-code">{{ c.code }}</span>
                        <span>{{ c.nom }}</span>
                    </div>
                    {% empty %}<span style="color:#d1d5db;font-style:italic;font-size:9px;">Non renseign\u00e9</span>
                    {% endfor %}
                </td>
                <td class="col-activ">{{ fiche.activites_professionnelles|default:""|linebreaksbr }}</td>
            </tr>
        </tbody>
    </table>

    <!-- PHOTOS (4 max) avec bouton recadrer -->
    <div class="photos-section">
        <div class="section-label">Photos :</div>
        <div class="photos-row">
            {% for photo in fiche.photos.all|slice:":4" %}
            <div class="photo-thumb">
                <div class="photo-crop-wrap">
                    <img src="{{ photo.image.url }}"
                         id="printImg_{{ photo.id }}"
                         data-src="{{ photo.image.url }}"
                         alt="{{ photo.legende|default:'Photo' }}"
                         onerror="this.closest('.photo-crop-wrap').innerHTML='<div class=photo-placeholder>Aucune image</div>';">
                </div>
                <button class="crop-btn no-print"
                        onclick="openCropModal('{{ photo.id }}', '{{ photo.image.url }}')"
                        title="Recadrer cette photo">
                    \u2702 Recadrer
                </button>
                {% if photo.legende %}
                <div class="caption">{{ photo.legende }}</div>
                {% endif %}
            </div>
            {% empty %}
            <div class="photo-placeholder" style="grid-column:span 4;font-size:9px;color:#94a3b8;font-style:italic;">Aucune photo ajout\u00e9e</div>
            {% endfor %}
        </div>
    </div>

    <!-- ==== ZONE QUI GRANDIT POUR REMPLIR LA PAGE ==== -->
    <div class="fiche-body">

        <!-- Description de la situation (flex:2) -->
        <div class="text-bloc bloc-orange grow" style="flex:2;">
            <div class="bloc-title">Description de la situation professionnelle :</div>
            <div class="bloc-body">{% if fiche.description_situation %}{{ fiche.description_situation }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}</div>
        </div>

        <!-- Observation (flex:2) -->
        <div class="text-bloc bloc-orange grow" style="flex:2;">
            <div class="bloc-title">Observation de l\u2019environnement de travail :</div>
            <div class="bloc-body">{% if fiche.observation_environnement %}{{ fiche.observation_environnement }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}</div>
        </div>

        <!-- Probl\u00e9matique (flex:1) -->
        <div class="text-bloc bloc-orange grow" style="flex:1;">
            <div class="bloc-title">Probl\u00e9matique :</div>
            <div class="bloc-body">{% if fiche.problematique %}{{ fiche.problematique }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}</div>
        </div>

        <!-- Grille : Savoirs | Mat\u00e9riels -->
        <div class="fiche-grid-2" style="flex:1.2;">
            <div class="text-bloc bloc-bleu">
                <div class="bloc-title">Pour cela, je dois conna\u00eetre :</div>
                <div class="bloc-body">{% if fiche.savoirs_necessaires %}{{ fiche.savoirs_necessaires }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}</div>
            </div>
            <div class="text-bloc bloc-gris">
                <div class="bloc-title">Je dispose (mat\u00e9riels, mat\u00e9riaux) :</div>
                <div class="bloc-body">{% if fiche.materiels_disponibles %}{{ fiche.materiels_disponibles }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}</div>
            </div>
        </div>

        <!-- Grille : Consigne | Risques EPI -->
        <div class="fiche-grid-2" style="flex:1.2;">
            <div class="text-bloc bloc-vert">
                <div class="bloc-title">Consigne de l\u2019entreprise :</div>
                <div class="bloc-body">{% if fiche.consigne_entreprise %}{{ fiche.consigne_entreprise }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}</div>
            </div>
            <div class="text-bloc bloc-rouge">
                <div class="bloc-title">Identifier les risques et d\u00e9duire les EPI :</div>
                <div class="bloc-body">{% if fiche.risques_epi %}{{ fiche.risques_epi }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}</div>
            </div>
        </div>

        {% if fiche.commentaire_prof %}
        <div class="text-bloc" style="border-color:#d97706;flex-shrink:0;">
            <div class="bloc-title" style="color:#92400e;">Commentaire enseignant :</div>
            <div class="bloc-body">{{ fiche.commentaire_prof }}</div>
        </div>
        {% endif %}

    </div><!-- /.fiche-body -->

    <!-- TAMPON VALIDATION (toujours en bas) -->
    <div class="flex-end" style="padding-top:4px;flex-shrink:0;">
        {% if fiche.validee_par_prof %}
        <div class="stamp-validated">
            <svg width="12" height="12" fill="none" stroke="#10b981" stroke-width="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" stroke-linecap="round" stroke-linejoin="round"></polyline></svg>
            Fiche valid\u00e9e \u2014 {{ fiche.date_modification|date:"d/m/Y" }}
        </div>
        {% else %}
        <span style="font-size:9px;color:#94a3b8;font-style:italic;">En attente de validation par l\u2019enseignant</span>
        {% endif %}
    </div>

</div>
{% endfor %}
""")

# ─── JAVASCRIPT ───────────────────────────────────────────────────────────────
parts.append("""
<script>
/* ================================================================
   RECADRAGE PHOTO (object-position X/Y)
================================================================ */
var _cropPhotoId = null;

function openCropModal(photoId, src) {
    _cropPhotoId = photoId;

    // Charger l'image dans le preview
    var previewImg = document.getElementById('cropPreviewImg');
    previewImg.src = src;

    // Restaurer les valeurs existantes de l'image imprim\u00e9e
    var printImg = document.getElementById('printImg_' + photoId);
    var pos = (printImg && printImg.style.objectPosition) ? printImg.style.objectPosition : '50% 50%';
    var parts = pos.replace(/%/g, '').trim().split(/\\s+/);
    var x = parseFloat(parts[0]) || 50;
    var y = parseFloat(parts[1] !== undefined ? parts[1] : 50) || 50;

    document.getElementById('cropX').value = x;
    document.getElementById('cropY').value = y;
    updateCropPreview();

    document.getElementById('cropModal').classList.add('open');
}

function updateCropPreview() {
    var x = document.getElementById('cropX').value;
    var y = document.getElementById('cropY').value;
    document.getElementById('cropXVal').textContent = x + '%';
    document.getElementById('cropYVal').textContent = y + '%';
    document.getElementById('cropPreviewImg').style.objectPosition = x + '% ' + y + '%';
}

function applyCrop() {
    var x = document.getElementById('cropX').value;
    var y = document.getElementById('cropY').value;
    var pos = x + '% ' + y + '%';
    var printImg = document.getElementById('printImg_' + _cropPhotoId);
    if (printImg) {
        printImg.style.objectPosition = pos;
    }
    closeCropModal();
}

function resetCrop() {
    document.getElementById('cropX').value = 50;
    document.getElementById('cropY').value = 50;
    updateCropPreview();
}

function closeCropModal() {
    document.getElementById('cropModal').classList.remove('open');
    _cropPhotoId = null;
}

// Fermer en cliquant sur le fond
document.getElementById('cropModal').addEventListener('click', function(e) {
    if (e.target === this) closeCropModal();
});
</script>
</body>
</html>
""")

# ─── ÉCRITURE DU FICHIER ──────────────────────────────────────────────────────
content = ''.join(parts)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"OK: {path}  ({len(content):,} caractères)")
