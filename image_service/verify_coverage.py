from apps.images.models import Image
import os

print('Final verification of image coverage...')
total_images = Image.objects.count()
images_with_files = 0
available_files = set(os.listdir('/service/media/images'))

for img in Image.objects.all():
    filename = os.path.basename(img.image_url)
    if filename in available_files:
        images_with_files += 1

print(f'Total images: {total_images}')
print(f'Images with files: {images_with_files}')
print(f'Coverage: {images_with_files/total_images*100:.1f}%')

if images_with_files == total_images:
    print('SUCCESS: All images now have corresponding files!')
else:
    print(f'Warning: {total_images - images_with_files} images still need files')
