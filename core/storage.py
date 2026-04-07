from cloudinary_storage.storage import MediaCloudinaryStorage, RESOURCE_TYPES
from cloudinary_storage import app_settings

# Chemins qui doivent TOUJOURS être stockés comme image Cloudinary (type IMAGE)
# Cela garantit des URLs image/upload même si l'extension manque ou est inconnue.
_FORCE_IMAGE_PATHS = frozenset(['portfolio/photos/'])

# Extensions image supplémentaires non couvertes par cloudinary_storage par défaut
_EXTRA_IMAGE_EXTS = frozenset(['heic', 'heif', 'avif', 'jfif', 'webp'])


class AutoMediaCloudinaryStorage(MediaCloudinaryStorage):
    """Storage that chooses Cloudinary resource type from file extension.

    - Paths in _FORCE_IMAGE_PATHS -> always image (e.g. portfolio photos)
    - common image extensions -> image
    - common video extensions -> video
    - everything else -> raw (PDFs, docs, archives)
    """

    def _get_resource_type(self, name):
        # Force IMAGE for known image-only upload paths (fixes portfolio photos)
        if name and any(p in name for p in _FORCE_IMAGE_PATHS):
            return RESOURCE_TYPES['IMAGE']

        extension = None
        if name and '.' in name:
            extension = name.rsplit('.', 1)[-1].lower()
        if extension and (extension in app_settings.STATIC_IMAGES_EXTENSIONS
                          or extension in _EXTRA_IMAGE_EXTS):
            return RESOURCE_TYPES['IMAGE']
        if extension and extension in app_settings.STATIC_VIDEOS_EXTENSIONS:
            return RESOURCE_TYPES['VIDEO']
        return RESOURCE_TYPES['RAW']
