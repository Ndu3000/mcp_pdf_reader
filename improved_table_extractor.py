#!/usr/bin/env python3
"""
Improved Table Extractor - Better structure detection and organization
"""

import cv2
import numpy as np
import pandas as pd
import easyocr
from typing import List, Tuple, Dict
import json

def load_and_preprocess_image(image_path: str) -> np.ndarray:
    """Load and preprocess image for better OCR results"""
    print(f"📸 Loading image: {image_path}")
    
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    print(f"🔍 Original image size: {img.shape[1]} x {img.shape[0]}")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding to improve text clarity
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 11, 2)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(thresh)
    
    # Save preprocessed image for inspection
    cv2.imwrite("preprocessed_table.png", denoised)
    print("💾 Saved preprocessed image as: preprocessed_table.png")
    
    return denoised

def detect_table_structure(img: np.ndarray) -> Dict:
    """Detect table lines and structure"""
    print("🔍 Detecting table structure...")
    
    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal_lines = cv2.morphologyEx(img, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    
    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    vertical_lines = cv2.morphologyEx(img, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    
    # Find contours for horizontal lines
    h_contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    horizontal_positions = []
    for contour in h_contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 50:  # Filter out noise
            horizontal_positions.append(y)
    
    # Find contours for vertical lines
    v_contours, _ = cv2.findContours(vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    vertical_positions = []
    for contour in v_contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h > 20:  # Filter out noise
            vertical_positions.append(x)
    
    horizontal_positions = sorted(set(horizontal_positions))
    vertical_positions = sorted(set(vertical_positions))
    
    print(f"📏 Found {len(horizontal_positions)} horizontal lines")
    print(f"📏 Found {len(vertical_positions)} vertical lines")
    
    return {
        'horizontal_lines': horizontal_positions,
        'vertical_lines': vertical_positions,
        'img_height': img.shape[0],
        'img_width': img.shape[1]
    }

def perform_ocr_with_regions(img: np.ndarray, structure: Dict) -> List[Dict]:
    """Perform OCR on specific table regions"""
    print("🔤 Performing OCR with regional analysis...")
    
    reader = easyocr.Reader(['en'])
    
    # Get all text with bounding boxes
    results = reader.readtext(img, detail=1)
    print(f"📝 Found {len(results)} text elements")
    
    # Organize text by regions
    organized_text = []
    
    for result in results:
        bbox = result[0]
        text = result[1]
        confidence = result[2]
        
        # Calculate center point
        center_x = sum([point[0] for point in bbox]) / 4
        center_y = sum([point[1] for point in bbox]) / 4
        
        # Determine row and column based on position
        row_idx = 0
        col_idx = 0
        
        # Find which row this text belongs to
        for i, h_line in enumerate(structure['horizontal_lines']):
            if center_y < h_line:
                row_idx = i
                break
        else:
            row_idx = len(structure['horizontal_lines'])
        
        # Find which column this text belongs to
        for i, v_line in enumerate(structure['vertical_lines']):
            if center_x < v_line:
                col_idx = i
                break
        else:
            col_idx = len(structure['vertical_lines'])
        
        organized_text.append({
            'text': text,
            'confidence': confidence,
            'row': row_idx,
            'col': col_idx,
            'center_x': center_x,
            'center_y': center_y,
            'bbox': bbox
        })
    
    return organized_text

def create_structured_table(organized_text: List[Dict]) -> pd.DataFrame:
    """Create a structured table from organized text"""
    print("📊 Creating structured table...")
    
    # Group by row and column
    table_dict = {}
    max_row = 0
    max_col = 0
    
    for item in organized_text:
        row = item['row']
        col = item['col']
        text = item['text']
        confidence = item['confidence']
        
        max_row = max(max_row, row)
        max_col = max(max_col, col)
        
        # Create key for this cell
        key = (row, col)
        
        # If cell already has text, append with space
        if key in table_dict:
            # Keep the text with higher confidence
            if confidence > table_dict[key]['confidence']:
                table_dict[key] = {'text': text, 'confidence': confidence}
        else:
            table_dict[key] = {'text': text, 'confidence': confidence}
    
    # Create DataFrame
    rows = []
    for r in range(max_row + 1):
        row_data = []
        for c in range(max_col + 1):
            key = (r, c)
            if key in table_dict:
                cell_text = table_dict[key]['text']
                # Clean up text
                cell_text = cell_text.strip()
                row_data.append(cell_text)
            else:
                row_data.append('')
        rows.append(row_data)
    
    # Create column names
    col_names = [f'Column_{i}' for i in range(max_col + 1)]
    
    df = pd.DataFrame(rows, columns=col_names)
    
    print(f"📋 Created table with {len(df)} rows and {len(df.columns)} columns")
    
    return df

def save_results(df: pd.DataFrame, organized_text: List[Dict], output_prefix: str = "improved_table"):
    """Save results in multiple formats"""
    
    # Save CSV
    csv_path = f"{output_prefix}.csv"
    df.to_csv(csv_path, index=False)
    print(f"💾 Saved CSV: {csv_path}")
    
    # Save Excel with formatting
    excel_path = f"{output_prefix}.xlsx"
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Table', index=False)
    print(f"💾 Saved Excel: {excel_path}")
    
    # Save detailed JSON with all OCR data
    json_path = f"{output_prefix}_detailed.json"
    detailed_data = {
        'table_data': df.to_dict('records'),
        'ocr_details': organized_text,
        'table_shape': df.shape
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(detailed_data, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved detailed JSON: {json_path}")
    
    # Print preview
    print("\n👀 Table Preview:")
    print("=" * 80)
    print(df.to_string(max_rows=10, max_cols=8))
    print("=" * 80)

def main():
    """Main extraction process"""
    image_path = "page_1_image_1.png"
    
    try:
        # Load and preprocess image
        img = load_and_preprocess_image(image_path)
        
        # Detect table structure
        structure = detect_table_structure(img)
        
        # Perform OCR with regional analysis
        organized_text = perform_ocr_with_regions(img, structure)
        
        # Create structured table
        df = create_structured_table(organized_text)
        
        # Save results
        save_results(df, organized_text)
        
        print("\n✅ Table extraction completed successfully!")
        print(f"📊 Extracted table shape: {df.shape}")
        
        # Additional analysis
        print("\n📈 Data Quality Analysis:")
        total_cells = df.shape[0] * df.shape[1]
        empty_cells = (df == '').sum().sum()
        filled_cells = total_cells - empty_cells
        print(f"   Total cells: {total_cells}")
        print(f"   Filled cells: {filled_cells}")
        print(f"   Empty cells: {empty_cells}")
        print(f"   Fill rate: {(filled_cells/total_cells)*100:.1f}%")
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        raise

if __name__ == "__main__":
    main()
