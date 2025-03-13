from PIL import Image
import os

def generate_pwa_icons(base_icon_path, output_dir):
    """Generate PWA icons in various sizes from a base icon"""
    sizes = [32, 72, 96, 128, 144, 152, 192, 384, 512]
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        with Image.open(base_icon_path) as img:
            # Generate icons for each size
            for size in sizes:
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                output_path = os.path.join(output_dir, f'icon-{size}x{size}.png')
                resized.save(output_path, 'PNG')
                print(f'Generated {size}x{size} icon')
            
            # Generate special icons
            # Badge for notifications
            badge = img.resize((72, 72), Image.Resampling.LANCZOS)
            badge.save(os.path.join(output_dir, 'badge-72x72.png'), 'PNG')
            print('Generated notification badge')
            
            # Apple touch icon
            apple_touch = img.resize((180, 180), Image.Resampling.LANCZOS)
            apple_touch.save(os.path.join(output_dir, 'apple-touch-icon.png'), 'PNG')
            print('Generated Apple touch icon')
            
            print('Icon generation complete!')
            
    except Exception as e:
        print(f'Error generating icons: {str(e)}')

if __name__ == '__main__':
    # Base icon should be at least 512x512 pixels
    base_icon_path = 'static/base_icon.png'
    output_dir = 'static/icons'
    
    if not os.path.exists(base_icon_path):
        print(f'Base icon not found at {base_icon_path}')
        print('Please provide a base icon of at least 512x512 pixels')
    else:
        generate_pwa_icons(base_icon_path, output_dir) 