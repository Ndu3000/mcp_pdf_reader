"""
OCR-based table extraction from the extracted image
Using EasyOCR to extract data from the actual table image
"""

import easyocr
import cv2
import numpy as np
from PIL import Image
import pandas as pd
import os

def extract_table_from_image(image_path: str):
    """Extract table data from the image using OCR"""
    
    print(f"🔍 Processing table image: {image_path}")
    print("=" * 60)
    
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return None
    
    try:
        # Initialize EasyOCR
        reader = easyocr.Reader(['en'])
        
        # Load image
        image = cv2.imread(image_path)
        print(f"📸 Image size: {image.shape[1]} x {image.shape[0]}")
        
        # Perform OCR
        print("🔤 Performing OCR...")
        results = reader.readtext(image)
        
        print(f"📝 Found {len(results)} text elements")
        
        # Sort results by Y coordinate (top to bottom) and then X coordinate (left to right)
        results.sort(key=lambda x: (x[0][0][1], x[0][0][0]))
        
        # Group by rows based on Y coordinates
        rows = []
        current_row = []
        tolerance = 20  # pixels tolerance for same row
        last_y = None
        
        for bbox, text, confidence in results:
            y_coord = bbox[0][1]  # Top Y coordinate
            
            if last_y is None or abs(y_coord - last_y) < tolerance:
                # Same row
                current_row.append((bbox, text, confidence))
                last_y = y_coord
            else:
                # New row
                if current_row:
                    rows.append(current_row)
                current_row = [(bbox, text, confidence)]
                last_y = y_coord
        
        # Add the last row
        if current_row:
            rows.append(current_row)
        
        print(f"📋 Organized into {len(rows)} rows")
        
        # Convert to structured data
        table_data = []
        
        for row_num, row in enumerate(rows):
            print(f"\n📖 Row {row_num + 1}:")
            
            # Sort elements in the row by X coordinate (left to right)
            row.sort(key=lambda x: x[0][0][0])
            
            row_data = []
            for bbox, text, confidence in row:
                print(f"   '{text}' (confidence: {confidence:.3f})")
                row_data.append(text.strip())
            
            table_data.append(row_data)
        
        # Create DataFrame
        if table_data:
            # Find the maximum number of columns
            max_cols = max(len(row) for row in table_data) if table_data else 0
            
            # Pad rows to have the same number of columns
            for row in table_data:
                while len(row) < max_cols:
                    row.append('')
            
            # Use first row as headers if it looks like headers
            if table_data:
                headers = table_data[0]
                data_rows = table_data[1:]
                
                # Create DataFrame
                df = pd.DataFrame(data_rows, columns=headers)
                
                print(f"\n📊 EXTRACTED TABLE:")
                print(f"   Shape: {df.shape[0]} rows × {df.shape[1]} columns")
                print(f"   Columns: {list(df.columns)}")
                
                # Save to CSV
                csv_filename = "image_extracted_table.csv"
                df.to_csv(csv_filename, index=False)
                print(f"\n💾 Saved to: {csv_filename}")
                
                # Show preview
                print(f"\n👀 Preview:")
                print(df.head(10).to_string(index=False))
                
                return df
        
        print("❌ No structured table data could be extracted")
        return None
        
    except Exception as e:
        print(f"❌ Error during OCR processing: {e}")
        return None

def main():
    image_path = "page_1_image_1.png"
    extract_table_from_image(image_path)

if __name__ == "__main__":
    main()
