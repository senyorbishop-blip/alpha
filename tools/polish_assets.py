import os
from PIL import Image
import json

# Define the paths
input_folder = 'input_assets/'  # Folder where input PNG assets are stored
output_folder = 'output_assets/'  # Folder where processed assets will be saved
manifest_file = 'manifest.json'

# Ensure output directory exists
os.makedirs(output_folder, exist_ok=True)

# Resize and process images
for file_name in os.listdir(input_folder):
    if file_name.endswith('.png'):
        # Open the image
        img_path = os.path.join(input_folder, file_name)
        img = Image.open(img_path)

        # Resize image
        img = img.resize((1024, 1024), Image.ANTIALIAS)

        # Color correction (Example - convert to RGB)
        img = img.convert('RGB')

        # Save PNG
        output_png_path = os.path.join(output_folder, file_name)
        img.save(output_png_path, 'PNG')

        # Generate WebP thumbnail
        thumbnail_path = os.path.join(output_folder, os.path.splitext(file_name)[0] + '.webp')
        img.save(thumbnail_path, 'WEBP', quality=80)

# Update the manifest.json
if os.path.exists(manifest_file):
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
else:
    manifest = {'assets': []}

# Add processed asset entries to manifest
for file_name in os.listdir(output_folder):
    manifest['assets'].append({'name': file_name, 'path': os.path.join(output_folder, file_name)})

# Save updated manifest
with open(manifest_file, 'w') as f:
    json.dump(manifest, f, indent=4)

print('Asset processing complete and manifest updated!')
