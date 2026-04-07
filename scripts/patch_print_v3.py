"""
Patch fiche_portfolio_print.html :
1. Ajoute CSS pour photos agrandies dans fiche-body
2. Supprime la section photos d'avant fiche-body
3. Réduit Observation (flex:2 -> flex:0.85 compact)
4. Insert la section photos APRÈS Problématique, avec flex:2
"""
import os, re

BASE = r"C:\Users\regis\OneDrive - CR HDF\Documents\plateforme_pedagogique v2 Copilote\plateforme-pedagogique"
path = os.path.join(BASE, "core", "templates", "core", "fiche_portfolio_print.html")

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# ── 1. Ajouter CSS pour photos agrandies (juste avant </style>) ───────────────
css_extra = """
/* Photos agrandies dans fiche-body (après problématique) */
.fiche-body .photos-section {
    flex: 2; display: flex; flex-direction: column; margin-bottom: 0;
}
.fiche-body .photos-section .photos-row {
    flex: 1; align-items: stretch; min-height: 0;
}
.fiche-body .photos-section .photo-thumb {
    display: flex; flex-direction: column; height: 100%;
}
.fiche-body .photos-section .photo-crop-wrap {
    flex: 1; height: auto !important; overflow: hidden;
}
.fiche-body .photos-section .photo-crop-wrap img {
    width: 100%; height: 100%; object-fit: cover; object-position: 50% 50%; display: block;
}
"""
OLD_STYLE_END = "    font-size: 11px; margin-right: auto;\n}\n</style>"
NEW_STYLE_END = "    font-size: 11px; margin-right: auto;\n}\n" + css_extra + "\n</style>"
assert OLD_STYLE_END in c, "ERREUR: ancre style non trouvée"
c = c.replace(OLD_STYLE_END, NEW_STYLE_END, 1)
print("1. CSS ajouté ✔")

# ── 2. Extraire la section photos (HTML complet, de <!-- PHOTOS à </div>\n\n) ──
PHOTO_START = "\n    <!-- PHOTOS (4 max) avec bouton recadrer -->\n"
PHOTO_END   = "\n    <!-- ==== ZONE QUI GRANDIT POUR REMPLIR LA PAGE ==== -->\n"
idx_start = c.find(PHOTO_START)
idx_end   = c.find(PHOTO_END)
assert idx_start != -1 and idx_end != -1, "ERREUR: ancres photos non trouvées"

photos_html = c[idx_start + len(PHOTO_START) : idx_end].rstrip("\n")
# Supprimer la section photos de sa position actuelle (entre table et fiche-body)
c = c[:idx_start] + "\n" + c[idx_end:]
print("2. Section photos extraite et supprimée ✔")

# ── 3. Réduire Observation (flex:2 → flex:0.85) ────────────────────────────────
OLD_OBS = '        <!-- Observation (flex:2) -->\n        <div class="text-bloc bloc-orange grow" style="flex:2;">'
NEW_OBS = '        <!-- Observation (réduit, ~taille ancienne section photos) -->\n        <div class="text-bloc bloc-orange grow" style="flex:0.85; min-height:60px;">'
assert OLD_OBS in c, "ERREUR: ancre Observation non trouvée"
c = c.replace(OLD_OBS, NEW_OBS, 1)
print("3. Observation réduite (flex:0.85) ✔")

# ── 4. Insérer photos après le bloc Problématique ─────────────────────────────
# L'ancre est la fin du bloc Problématique, juste avant "<!-- Grille : Savoirs"
OLD_AFTER_PROBL = "        <!-- Grille : Savoirs | Matériels -->"
photos_insert = "\n        <!-- PHOTOS (agrandies, flex:2 — déplacées après problématique) -->\n" + photos_html + "\n"
NEW_AFTER_PROBL = photos_insert + "\n        <!-- Grille : Savoirs | Matériels -->"
assert OLD_AFTER_PROBL in c, "ERREUR: ancre Savoirs non trouvée"
c = c.replace(OLD_AFTER_PROBL, NEW_AFTER_PROBL, 1)
print("4. Section photos insérée après Problématique ✔")

# ── Écriture ──────────────────────────────────────────────────────────────────
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print(f"\nOK: {path}  ({len(c):,} caractères)")
