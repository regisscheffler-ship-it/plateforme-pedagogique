import os
import cloudinary
import cloudinary.api

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True,
)

prefixes = [
    'media/ateliers/fichiers',
    'media/fichiers',
    'media/archives',
    'photos_profils',
    'media',
]

def list_resources(prefix, resource_type):
    try:
        res = cloudinary.api.resources(type='upload', resource_type=resource_type, prefix=prefix, max_results=100)
        items = res.get('resources', [])
        print(f"Prefix={prefix!r} resource_type={resource_type} count={len(items)}")
        for r in items[:10]:
            public_id = r.get('public_id')
            url = cloudinary.CloudinaryResource(public_id, default_resource_type=resource_type).url
            print('  -', public_id, url)
    except Exception as e:
        print(f"Error listing {prefix} {resource_type}: {e}")

if __name__ == '__main__':
    for prefix in prefixes:
        for rt in ('raw', 'image'):
            list_resources(prefix, rt)
