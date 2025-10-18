from apps.images.models import Image
import os

print('Checking database images against filesystem...')
has_files = 0
no_files = 0
available_files = set(os.listdir('/service/media/images'))

for img in Image.objects.all()[:100]:
    filename = os.path.basename(img.image_url)
    if filename in available_files:
        has_files += 1
    else:
        no_files += 1

print(f'Has files: {has_files}, No files: {no_files}')
print(f'Total files in filesystem: {len(available_files)}')
print(f'Total images in database: {Image.objects.count()}')
