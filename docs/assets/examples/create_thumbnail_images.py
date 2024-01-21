
# [Imports]
import argparse       # see https://docs.python.org/3/library/argparse.html
from PIL import Image # see https://pillow.readthedocs.io/en/stable/
log = print

# [Parameters]
fixed_width = 400.0
file_name = 'example_{name}.png'

# [Code]
# - Setup Parser
parser = argparse.ArgumentParser(
                    prog='create_thumbnail_images.py',
                    description='convert a image to a 400x400px image keeping the aspect ratio of the input',
                    epilog='please see the code in `docs/assets/examples/create_thumbnail_images.py` for more details` for details.')

parser.add_argument('filename')           # positional argument
parser.add_argument('-v', '--verbose',
                    action='store_true')  # on/off flag
args = parser.parse_args()

# - create output file name
file_name = args.filename
file_thumbnail_name = f'thumbnail_' + file_name.replace('example_', '')

def make_square(im, min_size=256, fill_color=(0, 0, 0, 0)):
    x, y = im.size
    size = max(min_size, x, y)
    new_im = Image.new('RGBA', (size, size), fill_color)
    new_im.paste(im, (int((size - x) / 2), int((size - y) / 2)))
    return new_im

# - Load the image 

if args.verbose:
    log(f'Loading image: {file_name}')

image = Image.open(file_name)
width = image.width
height = image.height

# - Calculate scaling
scale_factor = width / fixed_width
new_height =  height / scale_factor

if args.verbose:
    log(f'Image size: {width}x{height}')
    log(f'Scale factor: {scale_factor}')
    log(f'New size: {fixed_width}x{new_height}')

# - Resize the image
resized_image = image.resize((int(fixed_width), int(new_height)))   

# - Make the image square
resized_image = make_square(resized_image,min_size=int(fixed_width))

# - Save 

if args.verbose:    
    log(f'Saving image: {file_thumbnail_name}')

resized_image.save(file_thumbnail_name)

# [End]