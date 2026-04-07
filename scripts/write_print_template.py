"""Réécriture complète de fiche_portfolio_print.html pour correspondre au template papier."""
import os

BASE = r"C:\Users\regis\OneDrive - CR HDF\Documents\plateforme_pedagogique v2 Copilote\plateforme-pedagogique"
path = os.path.join(BASE, "core", "templates", "core", "fiche_portfolio_print.html")

TEMPLATE = """\
{% load static %}
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Portfolio \u2014 {{ portfolio.eleve.user.last_name }} {{ portfolio.eleve.user.first_name }}</title>
<style>
/* =============================================================
   RESET & BASE
   ============================================================= */
@page { size: A4 portrait; margin: 0; }
*, *::before, *::after { box-sizing: border-box; }
* { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }

body { font-family: Arial, Helvetica, sans-serif; background: #4b5563; margin: 0; font-size: 11px; }

/* ─── BARRE D'ACTIONS (masqu\u00e9e \u00e0 l'impression) ─────────────── */
.action-bar {
    background: white; padding: 10px 20px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.12);
    position: sticky; top: 0; z-index: 1000;
    display: flex; justify-content: center; align-items: center; gap: 16px;
    border-bottom: 4px solid #d97706; margin-bottom: 20px;
}
.btn {
    padding: 8px 16px; border: none; border-radius: 6px;
    font-size: 13px; font-weight: 600; cursor: pointer;
    display: inline-flex; align-items: center; gap: 6px;
    text-decoration: none;
}
.btn-back  { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
.btn-back:hover { background: #e5e7eb; }
.btn-print { background: #d97706; color: white; }
.btn-print:hover { background: #b45309; }
.bar-info  { font-size: 0.85rem; color: #6b7280; }

/* ─── FEUILLES A4 ────────────────────────────────────────── */
.sheet {
    background: white;
    width: 210mm;
    min-height: 297mm;
    margin: 20px auto;
    padding: 10mm 12mm;
    box-shadow: 0 0 15px rgba(0,0,0,0.4);
    display: flex; flex-direction: column; gap: 0;
}
@media print {
    body { background: none; }
    .sheet { margin: 0; box-shadow: none; padding: 8mm 10mm; page-break-after: always; }
    .sheet:last-child { page-break-after: avoid; }
    .no-print { display: none !important; }
}

/* ─── COUVERTURE ─────────────────────────────────────────── */
.cover-title {
    font-size: 26px; font-weight: 800; color: #1e293b;
    border-bottom: 4px solid #d97706; padding-bottom: 8px;
    margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.04em;
}
.cover-student-box {
    border: 2px solid #d97706; border-radius: 6px; padding: 12px 16px;
    background: #fffbeb; margin-bottom: 16px;
}
.cover-student-box .label { font-size: 9px; font-weight: 700; color: #92400e; text-transform: uppercase; }
.cover-student-box .value { font-size: 17px; font-weight: 800; color: #1e293b; margin-top: 2px; }
.cover-student-box .sub   { font-size: 11px; color: #64748b; margin-top: 2px; }
.cover-stats { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.cover-stat  { flex:1; min-width:70px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px 12px; text-align:center; }
.cover-stat-value { font-size:20px; font-weight:800; color:#d97706; display:block; }
.cover-stat-label { font-size:9px; color:#94a3b8; text-transform:uppercase; }
.cover-stat.green .cover-stat-value { color:#10b981; }
.cover-fiches-list { margin-top:12px; }
.cover-fiche-line { display:flex; align-items:center; gap:8px; padding:4px 0; border-bottom:1px solid #f1f5f9; font-size:10px; }
.cover-fiche-line .num    { font-weight:700; color:#d97706; min-width:20px; }
.cover-fiche-line .titre  { flex:1; color:#374151; }
.badge-sm { font-size:9px; font-weight:700; padding:2px 6px; border-radius:10px; text-transform:uppercase; letter-spacing:0.04em; }
.badge-formative    { background:#dbeafe; color:#1d4ed8; }
.badge-sommative    { background:#fce7f3; color:#9d174d; }
.badge-certificative{ background:#f3e8ff; color:#6d28d9; }
.badge-ok   { background:#d1fae5; color:#065f46; }
.badge-wait { background:#fef3c7; color:#92400e; }

/* ─── FICHE : EN-T\u00caTE ──────────────────────────────────────── */
.fiche-header {
    display: flex; align-items: flex-start; gap: 10px;
    border-bottom: 3px solid #d97706; padding-bottom: 8px; margin-bottom: 8px;
}
.fiche-header-logo {
    width: 54px; height: 54px; flex-shrink: 0;
    object-fit: contain;
}
.fiche-header-logo-placeholder {
    width: 54px; height: 54px; flex-shrink: 0;
    background: #fef3c7; border: 2px solid #d97706; border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 700; color: #92400e; text-align: center;
    line-height: 1.2;
}
.fiche-header-center {
    flex: 1; border: 2px solid #374151; border-radius: 4px;
    padding: 6px 10px; min-height: 48px;
    display: flex; align-items: center;
}
.fiche-header-title {
    font-size: 13px; font-weight: 800; color: #1e293b;
    line-height: 1.3;
}
.fiche-header-right {
    display: flex; flex-direction: column; align-items: flex-end; gap: 6px;
    flex-shrink: 0;
}
.fiche-header-eleve { font-size: 9px; color: #64748b; text-align: right; }
.fiche-header-eleve strong { color: #374151; }

/* Types (checkboxes visuels) */
.type-row { display: flex; gap: 8px; align-items: center; margin-top: 3px; }
.type-item { display: flex; align-items: center; gap: 3px; font-size: 9px; color: #374151; }
.type-box  {
    width: 12px; height: 12px; border: 1.5px solid #374151; border-radius: 2px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 8px; font-weight: 900; flex-shrink: 0;
}
.type-box.checked { background: #1e293b; color: white; }

/* ─── TABLE UNIT\u00c9 / COMP\u00c9TENCES / ACTIVIT\u00c9S ─────────────────── */
.fiche-table {
    width: 100%; border-collapse: collapse; font-size: 9.5px;
    margin-bottom: 7px;
}
.fiche-table th {
    background: #f1f5f9; color: #374151; font-weight: 700;
    border: 1.5px solid #94a3b8; padding: 4px 6px;
    font-size: 9px; text-align: left; text-transform: uppercase;
    letter-spacing: 0.04em;
}
.fiche-table td {
    border: 1.5px solid #94a3b8; padding: 5px 6px;
    vertical-align: top; line-height: 1.4; font-size: 9.5px; color: #374151;
    min-height: 28px;
}
.fiche-table .col-unite  { width: 22%; }
.fiche-table .col-comp   { width: 38%; }
.fiche-table .col-activ  { width: 40%; }
.comp-line { display: flex; align-items: baseline; gap: 4px; padding: 1px 0; }
.comp-code { font-size: 9px; font-weight: 700; color: #d97706; white-space: nowrap; }

/* ─── PHOTOS ─────────────────────────────────────────────── */
.photos-section {
    border: 2px solid #f59e0b; border-radius: 4px;
    padding: 5px 7px; margin-bottom: 6px;
}
.section-label {
    font-size: 9px; font-weight: 700; color: #92400e;
    text-transform: uppercase; letter-spacing: 0.05em;
    margin-bottom: 5px;
}
.photos-row {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px;
}
.photo-thumb {
    border-radius: 3px; overflow: hidden;
    border: 1px solid #e2e8f0; background: #f8fafc;
}
.photo-thumb img {
    width: 100%; height: 65px; object-fit: cover; display: block;
}
.photo-thumb .caption {
    font-size: 7px; color: #64748b; padding: 2px 4px;
    text-align: center; background: white; border-top: 1px solid #f1f5f9;
    overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
}
.photo-placeholder {
    height: 65px; display: flex; align-items: center; justify-content: center;
    background: #f8fafc; color: #d1d5db; font-size: 18px;
}

/* ─── BLOCS TEXTE (couleurs selon type) ─────────────────── */
.text-bloc {
    border: 2px solid #f59e0b; border-radius: 4px;
    padding: 5px 8px; margin-bottom: 6px;
    min-height: 48px;
}
.text-bloc .bloc-title {
    font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.05em; margin-bottom: 3px;
}
.text-bloc .bloc-body {
    font-size: 9.5px; color: #1e293b; line-height: 1.5;
    min-height: 24px; white-space: pre-wrap;
}
.text-bloc .empty { color: #d1d5db; font-style: italic; font-size: 9px; }

/* Orange : description, observation, probl\u00e9matique */
.bloc-orange { border-color: #f59e0b; }
.bloc-orange .bloc-title { color: #92400e; }

/* Bleu : savoirs */
.bloc-bleu { border-color: #3b82f6; }
.bloc-bleu .bloc-title { color: #1d4ed8; }

/* Gris : mat\u00e9riels */
.bloc-gris { border-color: #94a3b8; }
.bloc-gris .bloc-title { color: #374151; }

/* Vert : consigne */
.bloc-vert { border-color: #10b981; }
.bloc-vert .bloc-title { color: #065f46; }

/* Rouge : risques */
.bloc-rouge { border-color: #ef4444; }
.bloc-rouge .bloc-title { color: #991b1b; }

/* Grille 2 colonnes */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 6px; }

/* Validation stamp */
.stamp-validated {
    border: 2px solid #10b981; border-radius: 6px;
    padding: 4px 10px; display: inline-flex; align-items: center; gap: 5px;
    color: #065f46; font-size: 9px; font-weight: 700; margin-top: 4px;
}
.flex-end { display: flex; justify-content: flex-end; }
</style>
</head>
<body>

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
</div>

<!-- ══════════════════════════════════════════════════════════════ -->
<!-- COUVERTURE                                                     -->
<!-- ══════════════════════════════════════════════════════════════ -->
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
        <div style="font-size:10px;font-weight:700;color:#374151;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.05em;">Liste des fiches</div>
        {% for fiche in fiches %}
        <div class="cover-fiche-line">
            <span class="num">{{ forloop.counter }}.</span>
            <span class="titre">{{ fiche.titre }}</span>
            <span class="badge-sm badge-{{ fiche.type_evaluation }}">{{ fiche.get_type_evaluation_display }}</span>
            {% if fiche.validee_par_prof %}<span class="badge-sm badge-ok">\u2713 Valid\u00e9e</span>
            {% else %}<span class="badge-sm badge-wait">En attente</span>{% endif %}
        </div>
        {% empty %}
        <p style="color:#94a3b8;font-style:italic;font-size:10px;">Aucune fiche dans ce portfolio.</p>
        {% endfor %}
    </div>
</div>

<!-- ══════════════════════════════════════════════════════════════ -->
<!-- UNE PAGE PAR FICHE (layout copie paper)                       -->
<!-- ══════════════════════════════════════════════════════════════ -->
{% for fiche in fiches %}
<div class="sheet">

    <!-- ── EN-T\u00caTE : Logo | Titre | Type ─────────────────────── -->
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

    <!-- ── TABLEAU : Unit\u00e9 | Comp\u00e9tences | Activit\u00e9s ────────────── -->
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
                    {% empty %}<span style="color:#d1d5db;font-style:italic;font-size:9px;">Non renseign\u00e9</span>{% endfor %}
                </td>
                <td class="col-activ">{{ fiche.activites_professionnelles|default:""|linebreaksbr }}</td>
            </tr>
        </tbody>
    </table>

    <!-- ── PHOTOS (4 max par fiche) ──────────────────────── -->
    <div class="photos-section">
        <div class="section-label">Photos :</div>
        <div class="photos-row">
            {% for photo in fiche.photos.all|slice:":4" %}
            <div class="photo-thumb">
                <img src="{{ photo.image.url }}" alt="{{ photo.legende|default:'Photo' }}"
                     onerror="this.parentNode.innerHTML='<div class=photo-placeholder>&#128247;</div>';">\n
                {% if photo.legende %}
                <div class="caption">{{ photo.legende }}</div>
                {% endif %}
            </div>
            {% empty %}
            <div class="photo-placeholder" style="grid-column:span 4;font-size:9px;color:#94a3b8;font-style:italic;">Aucune photo ajout\u00e9e</div>
            {% endfor %}
        </div>
    </div>

    <!-- ── DESCRIPTION DE LA SITUATION ───────────────────── -->
    <div class="text-bloc bloc-orange">
        <div class="bloc-title">Description de la situation Professionnelle :</div>
        <div class="bloc-body">
            {% if fiche.description_situation %}{{ fiche.description_situation }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}
        </div>
    </div>

    <!-- ── OBSERVATION DE L'ENVIRONNEMENT ────────────────── -->
    <div class="text-bloc bloc-orange">
        <div class="bloc-title">Observation de son environnement de travail :</div>
        <div class="bloc-body">
            {% if fiche.observation_environnement %}{{ fiche.observation_environnement }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}
        </div>
    </div>

    <!-- ── PROBL\u00c9MATIQUE ─────────────────────────────────────── -->
    <div class="text-bloc bloc-orange" style="min-height:36px;">
        <div class="bloc-title">Probl\u00e9matique :</div>
        <div class="bloc-body">
            {% if fiche.problematique %}{{ fiche.problematique }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}
        </div>
    </div>

    <!-- ── GRILLE 2 COLONNES : Savoirs | Mat\u00e9riels ─────────── -->
    <div class="grid-2">
        <div class="text-bloc bloc-bleu" style="margin-bottom:0;">
            <div class="bloc-title">Pour cela, je dois conna\u00eetre :</div>
            <div class="bloc-body">
                {% if fiche.savoirs_necessaires %}{{ fiche.savoirs_necessaires }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}
            </div>
        </div>
        <div class="text-bloc bloc-gris" style="margin-bottom:0;">
            <div class="bloc-title">Je dispose (mat\u00e9riels, mat\u00e9riaux) :</div>
            <div class="bloc-body">
                {% if fiche.materiels_disponibles %}{{ fiche.materiels_disponibles }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}
            </div>
        </div>
    </div>

    <!-- ── GRILLE 2 COLONNES : Consigne | Risques/EPI ──── -->
    <div class="grid-2">
        <div class="text-bloc bloc-vert" style="margin-bottom:0;">
            <div class="bloc-title">Consigne de l\u2019entreprise :</div>
            <div class="bloc-body">
                {% if fiche.consigne_entreprise %}{{ fiche.consigne_entreprise }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}
            </div>
        </div>
        <div class="text-bloc bloc-rouge" style="margin-bottom:0;">
            <div class="bloc-title">Identifier les risques et d\u00e9duire les EPI :</div>
            <div class="bloc-body">
                {% if fiche.risques_epi %}{{ fiche.risques_epi }}{% else %}<span class="empty">Non renseign\u00e9</span>{% endif %}
            </div>
        </div>
    </div>

    <!-- ── COMMENTAIRE PROF ───────────────────────────────── -->
    {% if fiche.commentaire_prof %}
    <div class="text-bloc" style="border-color:#d97706;margin-top:6px;">
        <div class="bloc-title" style="color:#92400e;">Commentaire enseignant :</div>
        <div class="bloc-body">{{ fiche.commentaire_prof }}</div>
    </div>
    {% endif %}

    <!-- ── TAMPON VALIDATION ──────────────────────────────── -->
    <div class="flex-end" style="margin-top:auto;padding-top:6px;">
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

</body>
</html>
"""

with open(path, "w", encoding="utf-8") as f:
    f.write(TEMPLATE)

print(f"OK: {path} ({len(TEMPLATE)} caractères)")
