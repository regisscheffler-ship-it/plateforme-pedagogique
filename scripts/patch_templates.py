"""
Script de patch pour ajouter les 4 nouveaux champs portfolio dans les templates.
"""
import os

BASE = r"C:\Users\regis\OneDrive - CR HDF\Documents\plateforme_pedagogique v2 Copilote\plateforme-pedagogique"

# ── 1. fiche_portfolio_form.html (prof) ────────────────────────────────────────
form_path = os.path.join(BASE, "core", "templates", "core", "fiche_portfolio_form.html")
with open(form_path, "r", encoding="utf-8") as f:
    content = f.read()

# Trouver les bornes de la section à remplacer
start_marker = "   <!-- Contenu \u00e9l\u00e8ve (modifiable par le prof) -->"
end_marker   = "            <!-- Photos (uniquement en modification) -->"
start = content.find(start_marker)
end   = content.find(end_marker)

if start == -1 or end == -1:
    print(f"ERREUR: marqueurs introuvables dans {form_path}")
    print(f"  start={start}, end={end}")
else:
    new_block = """\
            <!-- Savoirs & Materiels (champs prof) -->
            <div class="form-section">
                <div class="form-section-title">Savoirs &amp; Mat\u00e9riels (Enseignant)</div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="id_savoirs">Pour cela, je dois conna\u00eetre</label>
                        <textarea name="savoirs_necessaires" id="id_savoirs" class="form-control" rows="4"
                                  placeholder="Notions, savoirs th\u00e9oriques n\u00e9cessaires\u2026">{{ fiche.savoirs_necessaires|default:'' }}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="id_materiels">Je dispose (mat\u00e9riels, mat\u00e9riaux)</label>
                        <textarea name="materiels_disponibles" id="id_materiels" class="form-control" rows="4"
                                  placeholder="Outils, mat\u00e9riaux, \u00e9quipements disponibles\u2026">{{ fiche.materiels_disponibles|default:'' }}</textarea>
                    </div>
                </div>
            </div>

            <!-- Contenu \u00e9l\u00e8ve (modifiable par le prof) -->
            <div class="form-section">
                <div class="form-section-title">Contenu \u00e9l\u00e8ve (description / observation / probl\u00e9matique)</div>

                <div class="form-group">
                    <label for="id_description_situation">Description de la situation de travail</label>
                    <textarea name="description_situation" id="id_description_situation" class="form-control" rows="4"
                              placeholder="D\u00e9crivez le contexte, le lieu, les personnes pr\u00e9sentes...">{{ fiche.description_situation|default:'' }}</textarea>
                </div>
                <div class="form-group">
                    <label for="id_observation_environnement">Observation de l\u2019environnement professionnel</label>
                    <textarea name="observation_environnement" id="id_observation_environnement" class="form-control" rows="4"
                              placeholder="Mat\u00e9riels utilis\u00e9s, conditions de travail, organisation...">{{ fiche.observation_environnement|default:'' }}</textarea>
                </div>
                <div class="form-group">
                    <label for="id_problematique">Probl\u00e9matique identifi\u00e9e</label>
                    <textarea name="problematique" id="id_problematique" class="form-control" rows="3"
                              placeholder="Quelle question / difficult\u00e9 l\u2019\u00e9l\u00e8ve a-t-il rencontr\u00e9e ?">{{ fiche.problematique|default:'' }}</textarea>
                </div>
                <div class="form-row" style="margin-top: 0.8rem;">
                    <div class="form-group">
                        <label for="id_consigne">Consigne de l\u2019entreprise</label>
                        <textarea name="consigne_entreprise" id="id_consigne" class="form-control" rows="3"
                                  placeholder="Consigne donn\u00e9e par le tuteur ou l\u2019entreprise\u2026">{{ fiche.consigne_entreprise|default:'' }}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="id_risques">Identifier les risques et d\u00e9duire les EPI</label>
                        <textarea name="risques_epi" id="id_risques" class="form-control" rows="3"
                                  placeholder="Risques identifi\u00e9s, \u00e9quipements de protection\u2026">{{ fiche.risques_epi|default:'' }}</textarea>
                    </div>
                </div>
            </div>

            """
    new_content = content[:start] + new_block + content[end:]
    with open(form_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"OK: {form_path}")


# ── 2. fiche_portfolio_eleve.html (update) ─────────────────────────────────────
eleve_path = os.path.join(BASE, "core", "templates", "core", "fiche_portfolio_eleve.html")
with open(eleve_path, "r", encoding="utf-8") as f:
    content = f.read()

# Ajouter 4 nouvelles zones élève après la zone problématique, avant la section photos
insert_after  = "                <div class=\"hint-text\">Ex : Comment optimiser\u2026 ? Pourquoi faut-il\u2026 ?</div>\n            </div>\n        </div>"
new_zones = """
        <!-- ═══ ZONES ÉLÈVE — SUITE ═══ -->
        <div class="info-section">
            <div class="section-heading">
                Analyse et consignes
                <span class="tag-eleve">\u00c9l\u00e8ve</span>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;">
                <div class="eleve-zone" style="border-color:#bfdbfe;">
                    <div class="eleve-zone-title" style="color:#1d4ed8;">&#128214; Pour cela, je dois conna\u00eetre</div>
                    <textarea name="savoirs_necessaires" class="form-textarea"
                              placeholder="Savoirs, notions, connaissances th\u00e9oriques n\u00e9cessaires\u2026"
                              {% if fiche.validee_par_prof %}disabled{% endif %}>{{ fiche.savoirs_necessaires }}</textarea>
                    <div class="hint-text">Ex : Je dois conna\u00eetre les normes\u2026, les propri\u00e9t\u00e9s\u2026</div>
                </div>
                <div class="eleve-zone" style="border-color:#d1d5db;">
                    <div class="eleve-zone-title">&#128295; Je dispose (mat\u00e9riels, mat\u00e9riaux)</div>
                    <textarea name="materiels_disponibles" class="form-textarea"
                              placeholder="Outils, mat\u00e9riaux et \u00e9quipements \u00e0 disposition\u2026"
                              {% if fiche.validee_par_prof %}disabled{% endif %}>{{ fiche.materiels_disponibles }}</textarea>
                    <div class="hint-text">Ex : J\u2019ai \u00e0 disposition\u2026, l\u2019atelier poss\u00e8de\u2026</div>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
                <div class="eleve-zone" style="border-color:#6ee7b7;">
                    <div class="eleve-zone-title" style="color:#065f46;">&#128203; Consigne de l\u2019entreprise</div>
                    <textarea name="consigne_entreprise" class="form-textarea" style="min-height:80px;"
                              placeholder="Quelle est la consigne ou mission donn\u00e9e par le tuteur\u2026"
                              {% if fiche.validee_par_prof %}disabled{% endif %}>{{ fiche.consigne_entreprise }}</textarea>
                    <div class="hint-text">Ex : Le chef de chantier m\u2019a demand\u00e9 de\u2026</div>
                </div>
                <div class="eleve-zone" style="border-color:#fca5a5;">
                    <div class="eleve-zone-title" style="color:#b91c1c;">&#9888;&#65039; Risques et EPI</div>
                    <textarea name="risques_epi" class="form-textarea" style="min-height:80px;"
                              placeholder="Risques identifi\u00e9s et \u00e9quipements de protection utilis\u00e9s\u2026"
                              {% if fiche.validee_par_prof %}disabled{% endif %}>{{ fiche.risques_epi }}</textarea>
                    <div class="hint-text">Ex : Risque de coupure \u2192 port de gants\u2026</div>
                </div>
            </div>
        </div>"""

if insert_after in content:
    new_content = content.replace(insert_after, insert_after + new_zones, 1)
    with open(eleve_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"OK: {eleve_path}")
else:
    print(f"ERREUR: marqueur intro non trouv\u00e9 dans {eleve_path}")
    idx = content.find("Comment optimiser")
    print(f"  idx Comment optimiser: {idx}")
    if idx > 0:
        print(repr(content[idx-50:idx+100]))


# ── 3. fiche_portfolio_eleve_create.html ───────────────────────────────────────
create_path = os.path.join(BASE, "core", "templates", "core", "fiche_portfolio_eleve_create.html")
with open(create_path, "r", encoding="utf-8") as f:
    content = f.read()

# Insérer les 4 nouvelles zones après la zone problématique
insert_after2 = "                <div class=\"hint-text\">Ex : Comment optimiser\u2026 ? Pourquoi faut-il\u2026 ?</div>\n            </div>\n        </div>"
new_zones_create = """
        <!-- ANALYSE ET CONSIGNES -->
        <div class="info-section">
            <div class="section-heading">
                Analyse et consignes
                <span class="tag-eleve">\u00c9l\u00e8ve</span>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;">
                <div class="eleve-zone" style="border-color:#bfdbfe;">
                    <div class="eleve-zone-title" style="color:#1d4ed8;">&#128214; Pour cela, je dois conna\u00eetre</div>
                    <textarea name="savoirs_necessaires" class="form-textarea"
                              placeholder="Savoirs, notions, connaissances th\u00e9oriques n\u00e9cessaires\u2026">{{ request.POST.savoirs_necessaires|default:'' }}</textarea>
                    <div class="hint-text">Ex : Je dois conna\u00eetre les normes\u2026</div>
                </div>
                <div class="eleve-zone" style="border-color:#d1d5db;">
                    <div class="eleve-zone-title">&#128295; Je dispose (mat\u00e9riels, mat\u00e9riaux)</div>
                    <textarea name="materiels_disponibles" class="form-textarea"
                              placeholder="Outils, mat\u00e9riaux et \u00e9quipements \u00e0 disposition\u2026">{{ request.POST.materiels_disponibles|default:'' }}</textarea>
                    <div class="hint-text">Ex : J\u2019ai \u00e0 disposition\u2026</div>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
                <div class="eleve-zone" style="border-color:#6ee7b7;">
                    <div class="eleve-zone-title" style="color:#065f46;">&#128203; Consigne de l\u2019entreprise</div>
                    <textarea name="consigne_entreprise" class="form-textarea" style="min-height:70px;"
                              placeholder="Consigne ou mission donn\u00e9e par le tuteur\u2026">{{ request.POST.consigne_entreprise|default:'' }}</textarea>
                </div>
                <div class="eleve-zone" style="border-color:#fca5a5;">
                    <div class="eleve-zone-title" style="color:#b91c1c;">&#9888;&#65039; Risques et EPI</div>
                    <textarea name="risques_epi" class="form-textarea" style="min-height:70px;"
                              placeholder="Risques identifi\u00e9s, \u00e9quipements de protection\u2026">{{ request.POST.risques_epi|default:'' }}</textarea>
                </div>
            </div>
        </div>"""

if insert_after2 in content:
    new_content = content.replace(insert_after2, insert_after2 + new_zones_create, 1)
    with open(create_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"OK: {create_path}")
else:
    print(f"ERREUR: marqueur non trouv\u00e9 dans {create_path}")
    idx = content.find("Comment optimiser")
    print(f"  idx: {idx}")
    if idx > 0:
        print(repr(content[idx-50:idx+120]))

print("Patch terminé.")
