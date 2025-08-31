"""
Extract and analyze embedded images from PDF
"""

import fitz  # PyMuPDF
import base64
from PIL import Image
import io
import os

def extract_images_from_pdf(pdf_path: str):
    """Extract embedded images from PDF and save them"""
    
    print(f"🖼️  Extracting images from: {pdf_path}")
    print("=" * 60)
    
    try:
        doc = fitz.open(pdf_path)
        
        total_images = 0
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            # Get images
            image_list = page.get_images()
            print(f"📃 Page {page_num + 1}: Found {len(image_list)} images")
            
            for img_index, img in enumerate(image_list):
                total_images += 1
                
                # Get image data
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                
                if pix.n < 5:  # GRAY or RGB
                    img_filename = f"page_{page_num + 1}_image_{img_index + 1}.png"
                    pix.save(img_filename)
                    print(f"   ✅ Saved: {img_filename}")
                    print(f"      Size: {pix.width} x {pix.height}")
                    print(f"      Colorspace: {pix.colorspace}")
                else:  # CMYK: convert to RGB first
                    pix1 = fitz.Pixmap(fitz.csRGB, pix)
                    img_filename = f"page_{page_num + 1}_image_{img_index + 1}.png"
                    pix1.save(img_filename)
                    print(f"   ✅ Saved (converted from CMYK): {img_filename}")
                    print(f"      Size: {pix1.width} x {pix1.height}")
                    pix1 = None
                
                pix = None
        
        print(f"\n📊 Total images extracted: {total_images}")
        doc.close()
        
        # Also try to extract from HTML
        print(f"\n🔍 Extracting base64 images from HTML...")
        html_file = "pdf_html_extract.html"
        if os.path.exists(html_file):
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Find base64 image data
            import re
            base64_pattern = r'data:image/png;base64,([A-Za-z0-9+/=]+)'
            matches = re.findall(base64_pattern, html_content)
            
            print(f"   Found {len(matches)} base64 images in HTML")
            
            for i, base64_data in enumerate(matches):
                try:
                    # Decode base64 image
                    image_data = base64.b64decode(base64_data)
                    image = Image.open(io.BytesIO(image_data))
                    
                    img_filename = f"html_extracted_image_{i + 1}.png"
                    image.save(img_filename)
                    print(f"   ✅ Saved from HTML: {img_filename}")
                    print(f"      Size: {image.width} x {image.height}")
                    print(f"      Mode: {image.mode}")
                    
                    # Show some stats about the image
                    if image.mode in ['RGB', 'L']:
                        print(f"      This appears to be the table image!")
                        
                except Exception as e:
                    print(f"   ❌ Error processing base64 image {i + 1}: {e}")
        
    except Exception as e:
        print(f"❌ Error extracting images: {e}")

def main():
    pdf_path = "../test.pdf"
    extract_images_from_pdf(pdf_path)

if __name__ == "__main__":
    main()
