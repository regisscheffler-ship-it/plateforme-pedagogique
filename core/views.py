
"""Facade module: expose the merged AST-generated views.

This file imports all symbols from `views_merged_ast.py` (the cleaned merge)
and provides small compatibility aliases expected by `core/urls.py`.
"""

from .views_merged_ast import *  # noqa: F401,F403

# Compat alias: older URLs expect `export_annuel_complet`.
try:
	export_annuel_complet = archives_export
except NameError:
	pass

