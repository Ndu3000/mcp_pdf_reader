#!/usr/bin/env python3
"""
MCP-Based PDF Table Extractor
Combines multiple extraction methods: PyMuPDF, Camelot, Tabula, and OCR
Similar to platform tools with fallback strategies
"""

import fitz  # PyMuPDF
import pandas as pd
import camelot
import tabula
from PIL import Image
import pytesseract
import cv2
import numpy as np
import easyocr
import io
import os
import json
from typing import Dict, List, Optional, Union
from pathlib import Path

class MCPPDFTableExtractor:
    """
    MCP-Compatible PDF Table Extractor
    Implements multiple extraction strategies with intelligent fallbacks
    """
    
    def __init__(self, pdf_path: str):
        """Initialize the extractor with a PDF file"""
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.doc = fitz.open(str(self.pdf_path))
        self.extraction_results = {}
        
        # Initialize OCR readers
        try:
            self.easyocr_reader = easyocr.Reader(['en'])
            self.ocr_available = True
        except Exception as e:
            print(f"⚠️  EasyOCR not available: {e}")
            self.ocr_available = False
    
    def get_pdf_info(self) -> Dict:
        """Get basic PDF information"""
        info = {
            'filename': self.pdf_path.name,
            'page_count': len(self.doc),
            'file_size': self.pdf_path.stat().st_size,
            'metadata': self.doc.metadata
        }
        return info
    
    def extract_text_pymupdf(self) -> str:
        """Extract all text using PyMuPDF"""
        print("📄 Extracting text with PyMuPDF...")
        text = ""
        for page_num, page in enumerate(self.doc):
            page_text = page.get_text()
            text += f"\n--- Page {page_num + 1} ---\n{page_text}"
        
        self.extraction_results['text_pymupdf'] = text
        return text
    
    def extract_tables_camelot(self, flavor: str = 'lattice') -> List[pd.DataFrame]:
        """Extract tables using Camelot (best for well-formatted PDFs)"""
        print(f"🔲 Extracting tables with Camelot ({flavor})...")
        tables = []
        
        try:
            # Try lattice flavor first (for tables with visible borders)
            camelot_tables = camelot.read_pdf(str(self.pdf_path), pages='all', flavor=flavor)
            
            if len(camelot_tables) == 0 and flavor == 'lattice':
                # Fallback to stream flavor (for tables without borders)
                print("🔄 Retrying with stream flavor...")
                camelot_tables = camelot.read_pdf(str(self.pdf_path), pages='all', flavor='stream')
            
            for i, table in enumerate(camelot_tables):
                df = table.df
                # Add metadata
                df.attrs = {
                    'page': table.page,
                    'method': f'camelot_{flavor}',
                    'confidence': getattr(table, 'accuracy', 0.0),
                    'table_index': i
                }
                tables.append(df)
                print(f"   📋 Found table {i+1} on page {table.page}: {df.shape}")
        
        except Exception as e:
            print(f"❌ Camelot extraction failed: {e}")
        
        self.extraction_results[f'tables_camelot_{flavor}'] = tables
        return tables
    
    def extract_tables_tabula(self) -> List[pd.DataFrame]:
        """Extract tables using Tabula (good for various PDF types)"""
        print("📊 Extracting tables with Tabula...")
        tables = []
        
        try:
            tabula_tables = tabula.read_pdf(str(self.pdf_path), pages='all', multiple_tables=True)
            
            for i, df in enumerate(tabula_tables):
                if isinstance(df, pd.DataFrame) and not df.empty:
                    # Add metadata
                    df.attrs = {
                        'method': 'tabula',
                        'table_index': i,
                        'confidence': 0.8  # Default confidence for Tabula
                    }
                    tables.append(df)
                    print(f"   📋 Found table {i+1}: {df.shape}")
        
        except Exception as e:
            print(f"❌ Tabula extraction failed: {e}")
        
        self.extraction_results['tables_tabula'] = tables
        return tables
    
    def extract_images_for_ocr(self) -> List[Dict]:
        """Extract images from PDF for OCR processing"""
        print("🖼️  Extracting images for OCR...")
        images = []
        
        for page_num, page in enumerate(self.doc):
            # Get page as image
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")
            
            # Convert to PIL Image
            img = Image.open(io.BytesIO(img_data))
            
            # Save image for debugging
            img_path = f"page_{page_num + 1}_full.png"
            img.save(img_path)
            
            images.append({
                'page': page_num + 1,
                'image': img,
                'image_path': img_path,
                'size': img.size
            })
            
            print(f"   📷 Page {page_num + 1}: {img.size}")
        
        return images
    
    def extract_with_ocr_easyocr(self, images: List[Dict]) -> List[pd.DataFrame]:
        """Extract tables using EasyOCR"""
        if not self.ocr_available:
            print("⚠️  EasyOCR not available, skipping OCR extraction")
            return []
        
        print("🔤 Extracting tables with EasyOCR...")
        tables = []
        
        for img_data in images:
            page_num = img_data['page']
            img = img_data['image']
            
            print(f"   🔍 Processing page {page_num}...")
            
            # Convert PIL to numpy array
            img_array = np.array(img)
            
            # Perform OCR
            results = self.easyocr_reader.readtext(img_array, detail=1)
            
            if results:
                # Organize text by position to detect table structure
                table_df = self._organize_ocr_text_to_table(results, page_num)
                if table_df is not None and not table_df.empty:
                    table_df.attrs = {
                        'page': page_num,
                        'method': 'easyocr',
                        'confidence': np.mean([result[2] for result in results]),
                        'text_elements': len(results)
                    }
                    tables.append(table_df)
                    print(f"   📋 Found table on page {page_num}: {table_df.shape}")
        
        self.extraction_results['tables_easyocr'] = tables
        return tables
    
    def extract_with_pytesseract(self, images: List[Dict]) -> str:
        """Extract text using Pytesseract"""
        print("🔤 Extracting text with Pytesseract...")
        full_text = ""
        
        for img_data in images:
            page_num = img_data['page']
            img = img_data['image']
            
            try:
                # Use Pytesseract for text extraction
                page_text = pytesseract.image_to_string(img)
                full_text += f"\n--- Page {page_num} (OCR) ---\n{page_text}"
                print(f"   📄 Page {page_num}: {len(page_text)} characters")
            except Exception as e:
                print(f"❌ Pytesseract failed on page {page_num}: {e}")
        
        self.extraction_results['text_pytesseract'] = full_text
        return full_text
    
    def _organize_ocr_text_to_table(self, ocr_results: List, page_num: int) -> Optional[pd.DataFrame]:
        """Organize OCR text results into a table structure"""
        if not ocr_results:
            return None
        
        # Sort by Y coordinate (top to bottom), then X coordinate (left to right)
        sorted_results = sorted(ocr_results, key=lambda x: (x[0][0][1], x[0][0][0]))
        
        # Group text by approximate Y coordinates (rows)
        rows = []
        current_row = []
        current_y = None
        y_threshold = 20  # Pixel threshold for same row
        
        for result in sorted_results:
            bbox = result[0]
            text = result[1].strip()
            confidence = result[2]
            
            if not text:
                continue
            
            # Calculate center Y coordinate
            center_y = (bbox[0][1] + bbox[2][1]) / 2
            
            if current_y is None:
                current_y = center_y
                current_row = [(text, bbox[0][0], confidence)]
            elif abs(center_y - current_y) <= y_threshold:
                # Same row
                current_row.append((text, bbox[0][0], confidence))
            else:
                # New row
                if current_row:
                    # Sort current row by X coordinate
                    current_row.sort(key=lambda x: x[1])
                    rows.append([item[0] for item in current_row])
                current_row = [(text, bbox[0][0], confidence)]
                current_y = center_y
        
        # Add last row
        if current_row:
            current_row.sort(key=lambda x: x[1])
            rows.append([item[0] for item in current_row])
        
        if not rows:
            return None
        
        # Create DataFrame
        # Find maximum number of columns
        max_cols = max(len(row) for row in rows) if rows else 0
        
        # Pad rows to have same number of columns
        padded_rows = []
        for row in rows:
            padded_row = row + [''] * (max_cols - len(row))
            padded_rows.append(padded_row)
        
        # Create column names
        col_names = [f'Column_{i}' for i in range(max_cols)]
        
        df = pd.DataFrame(padded_rows, columns=col_names)
        return df
    
    def detect_table_structure_from_text(self, text: str) -> Optional[pd.DataFrame]:
        """Parse text to detect table-like structures"""
        print("🔍 Detecting table structure from text...")
        
        lines = text.split('\n')
        table_data = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for lines with multiple columns (separated by multiple spaces or tabs)
            # Split by multiple whitespace characters
            import re
            columns = re.split(r'\s{2,}', line)
            
            # Consider it a table row if it has multiple columns
            if len(columns) >= 3:
                table_data.append(columns)
        
        if len(table_data) > 1:  # Need at least 2 rows for a table
            # Use first row as headers if it looks like headers
            headers = table_data[0]
            data_rows = table_data[1:]
            
            # Ensure all rows have the same number of columns
            max_cols = max(len(row) for row in table_data)
            
            padded_headers = headers + [''] * (max_cols - len(headers))
            padded_data = []
            
            for row in data_rows:
                padded_row = row + [''] * (max_cols - len(row))
                padded_data.append(padded_row)
            
            df = pd.DataFrame(padded_data, columns=padded_headers)
            df.attrs = {
                'method': 'text_structure_detection',
                'confidence': 0.6
            }
            
            print(f"   📋 Detected table structure: {df.shape}")
            return df
        
        return None
    
    def extract_all_methods(self) -> Dict:
        """Run all extraction methods and return comprehensive results"""
        print("🚀 Starting comprehensive PDF extraction...")
        print("=" * 60)
        
        pdf_info = self.get_pdf_info()
        print(f"📄 Processing: {pdf_info['filename']}")
        print(f"📊 Pages: {pdf_info['page_count']}")
        print(f"💾 Size: {pdf_info['file_size']:,} bytes")
        
        all_results = {
            'pdf_info': pdf_info,
            'extraction_methods': {},
            'best_tables': [],
            'all_text': ""
        }
        
        # Method 1: PyMuPDF text extraction
        text_pymupdf = self.extract_text_pymupdf()
        all_results['all_text'] += text_pymupdf
        
        # Method 2: Camelot table extraction (lattice)
        tables_camelot_lattice = self.extract_tables_camelot('lattice')
        all_results['extraction_methods']['camelot_lattice'] = tables_camelot_lattice
        
        # Method 3: Camelot table extraction (stream)
        tables_camelot_stream = self.extract_tables_camelot('stream')
        all_results['extraction_methods']['camelot_stream'] = tables_camelot_stream
        
        # Method 4: Tabula table extraction
        tables_tabula = self.extract_tables_tabula()
        all_results['extraction_methods']['tabula'] = tables_tabula
        
        # Method 5: Image extraction for OCR
        images = self.extract_images_for_ocr()
        
        # Method 6: EasyOCR table extraction
        tables_easyocr = self.extract_with_ocr_easyocr(images)
        all_results['extraction_methods']['easyocr'] = tables_easyocr
        
        # Method 7: Pytesseract text extraction
        text_pytesseract = self.extract_with_pytesseract(images)
        all_results['all_text'] += "\n" + text_pytesseract
        
        # Method 8: Text structure detection
        table_from_text = self.detect_table_structure_from_text(all_results['all_text'])
        if table_from_text is not None:
            all_results['extraction_methods']['text_structure'] = [table_from_text]
        
        # Determine best tables
        best_tables = self._select_best_tables(all_results['extraction_methods'])
        all_results['best_tables'] = best_tables
        
        # Save comprehensive results
        self._save_all_results(all_results)
        
        print("\n✅ Extraction completed!")
        self._print_summary(all_results)
        
        return all_results
    
    def _select_best_tables(self, extraction_methods: Dict) -> List[pd.DataFrame]:
        """Select the best tables from all extraction methods"""
        print("\n🎯 Selecting best tables...")
        
        all_tables = []
        
        # Collect all tables with scoring
        for method, tables in extraction_methods.items():
            if not tables:
                continue
            
            for table in tables:
                if isinstance(table, pd.DataFrame) and not table.empty:
                    score = self._score_table(table, method)
                    all_tables.append((table, score, method))
        
        # Sort by score (highest first)
        all_tables.sort(key=lambda x: x[1], reverse=True)
        
        # Select best tables (avoid duplicates)
        best_tables = []
        seen_shapes = set()
        
        for table, score, method in all_tables:
            table_signature = (table.shape, method)
            if table_signature not in seen_shapes:
                best_tables.append(table)
                seen_shapes.add(table_signature)
                print(f"   ✅ Selected {method} table: {table.shape} (score: {score:.2f})")
                
                if len(best_tables) >= 3:  # Limit to top 3 tables
                    break
        
        return best_tables
    
    def _score_table(self, table: pd.DataFrame, method: str) -> float:
        """Score a table based on various quality metrics"""
        score = 0.0
        
        # Base scores by method reliability
        method_scores = {
            'camelot_lattice': 0.9,
            'camelot_stream': 0.8,
            'tabula': 0.7,
            'easyocr': 0.6,
            'text_structure': 0.4
        }
        
        score += method_scores.get(method, 0.5)
        
        # Size bonus (larger tables often better)
        size_bonus = min(table.shape[0] * table.shape[1] / 100, 0.3)
        score += size_bonus
        
        # Non-empty cells bonus
        total_cells = table.shape[0] * table.shape[1]
        non_empty = table.astype(str).apply(lambda x: x.str.strip() != '').sum().sum()
        fill_rate = non_empty / total_cells if total_cells > 0 else 0
        score += fill_rate * 0.3
        
        # Confidence bonus (if available)
        if hasattr(table, 'attrs') and 'confidence' in table.attrs:
            score += table.attrs['confidence'] * 0.2
        
        return score
    
    def _save_all_results(self, results: Dict):
        """Save all extraction results"""
        print("\n💾 Saving results...")
        
        # Save best tables as CSV
        for i, table in enumerate(results['best_tables'], 1):
            csv_path = f"mcp_extracted_table_{i}.csv"
            table.to_csv(csv_path, index=False)
            print(f"   📄 Saved {csv_path}")
        
        # Save all tables by method
        os.makedirs("mcp_extraction_details", exist_ok=True)
        
        for method, tables in results['extraction_methods'].items():
            if tables:
                for j, table in enumerate(tables, 1):
                    csv_path = f"mcp_extraction_details/{method}_table_{j}.csv"
                    table.to_csv(csv_path, index=False)
        
        # Save extraction summary
        summary = {
            'pdf_info': results['pdf_info'],
            'extraction_summary': {
                method: len(tables) for method, tables in results['extraction_methods'].items()
            },
            'best_tables_count': len(results['best_tables'])
        }
        
        with open("mcp_extraction_summary.json", 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"   📊 Saved extraction summary")
    
    def _print_summary(self, results: Dict):
        """Print extraction summary"""
        print("\n📈 EXTRACTION SUMMARY:")
        print("=" * 60)
        
        total_tables = 0
        for method, tables in results['extraction_methods'].items():
            count = len(tables) if tables else 0
            total_tables += count
            print(f"   {method:20}: {count} tables")
        
        print(f"\n   {'Total tables found':20}: {total_tables}")
        print(f"   {'Best tables selected':20}: {len(results['best_tables'])}")
        
        print(f"\n📁 Output files:")
        print(f"   • mcp_extracted_table_*.csv (best tables)")
        print(f"   • mcp_extraction_details/ (all tables)")
        print(f"   • mcp_extraction_summary.json (summary)")

def main():
    """Main extraction function - MCP tool entry point"""
    
    # For testing, use the test PDF
    pdf_path = "test.pdf"
    
    if not os.path.exists(pdf_path):
        # Try alternative paths
        alternative_paths = [
            "../test.pdf",
            "../frontend/test.pdf",
            "page_1_image_1.png"
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                if alt_path.endswith('.png'):
                    print(f"⚠️  Found image file instead of PDF: {alt_path}")
                    print("💡 Using image-based extraction...")
                    # TODO: Implement direct image processing
                    return
                else:
                    pdf_path = alt_path
                    break
        else:
            print(f"❌ PDF file not found: {pdf_path}")
            print("📂 Available files:")
            for file in os.listdir('.'):
                if file.endswith(('.pdf', '.png', '.jpg')):
                    print(f"   {file}")
            return
    
    try:
        # Initialize extractor
        extractor = MCPPDFTableExtractor(pdf_path)
        
        # Run comprehensive extraction
        results = extractor.extract_all_methods()
        
        print(f"\n🎉 MCP PDF extraction completed successfully!")
        print(f"📊 Found {len(results['best_tables'])} high-quality tables")
        
    except Exception as e:
        print(f"❌ Error during MCP extraction: {e}")
        raise

if __name__ == "__main__":
    main()
