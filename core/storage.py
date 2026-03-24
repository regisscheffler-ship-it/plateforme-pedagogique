from cloudinary_storage.storage import MediaCloudinaryStorage, RESOURCE_TYPES
from cloudinary_storage import app_settings


class AutoMediaCloudinaryStorage(MediaCloudinaryStorage):
    """Storage that chooses Cloudinary resource type from file extension.

    - common image extensions -> image
    - common video extensions -> video
    - everything else -> raw (PDFs, docs, archives)
    """

    def _get_resource_type(self, name):
        extension = None
        if name and '.' in name:
            extension = name.split('.')[-1].lower()
        if extension and extension in app_settings.STATIC_IMAGES_EXTENSIONS:
            return RESOURCE_TYPES['IMAGE']
        if extension and extension in app_settings.STATIC_VIDEOS_EXTENSIONS:
            return RESOURCE_TYPES['VIDEO']
        return RESOURCE_TYPES['RAW']
