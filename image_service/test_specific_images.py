from apps.images.models import Image
import os

print('Testing specific images mentioned by user...')
test_images = ['748SS8SW.jpg', '742TKGXF.jpg', '7401BDP3.jpg', '73UHJURH.jpg', '73RO9EML.jpg']
available_files = set(os.listdir('/service/media/images'))

print('Testing specific images:')
for img in test_images:
    status = "FOUND" if img in available_files else "NOT FOUND"
    print(f'{img}: {status}')

print('\nChecking database records for these images:')
for img in test_images:
    try:
        db_img = Image.objects.get(image_url=f"/media/images/{img}")
        print(f'{img}: Database record exists - {db_img.title}')
    except Image.DoesNotExist:
        print(f'{img}: No database record found')
    except Image.MultipleObjectsReturned:
        print(f'{img}: Multiple database records found')
