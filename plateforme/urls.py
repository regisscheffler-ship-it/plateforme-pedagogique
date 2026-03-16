from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse


def root_probe(request):
    """Lightweight root response to satisfy platform health checks.
    Returns a small HTML that redirects clients to the app dashboard,
    but responds 200 OK so external health probes succeed.
    """
    html = """
    <!doctype html>
    <html><head>
    <meta http-equiv="refresh" content="0;url=/dashboard/eleve/">
    <title>Plateforme pédagogique</title>
    </head><body>
    <p>Redirection vers l'application — <a href="/dashboard/eleve/">ouvrir le tableau de bord</a></p>
    </body></html>
    """
    return HttpResponse(html)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_probe),
    path('', include('core.urls')),  # Toutes les URLs sont dans core.urls
]

# Gestion des fichiers media en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)