#!/usr/bin/env python3
"""
Test script for MCP PDF Tool - Direct function testing
"""

# Import the extractor directly instead of the MCP wrapper
from mcp_comprehensive_extractor import MCPPDFTableExtractor
import json
import os
from pathlib import Path

def test_pdf_extraction_directly():
    """Test the PDF extraction functionality directly"""
    
    print('📄 Testing MCP PDF Extraction (Direct Mode)')
    print('=' * 50)

    # Test 1: List available PDFs
    print('\n1. Listing available PDFs:')
    pdf_files = []
    for file_path in Path('.').glob("*.pdf"):
        file_info = {
            "filename": file_path.name,
            "path": str(file_path),
            "size": file_path.stat().st_size
        }
        pdf_files.append(file_info)
    
    print(f"Found {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"   {pdf['filename']} ({pdf['size']:,} bytes)")

    # Test 2: Test with the available PDF
    if pdf_files:
        test_pdf = pdf_files[0]['path']
        print(f'\n2. Testing with PDF: {test_pdf}')
        
        try:
            # Initialize extractor
            extractor = MCPPDFTableExtractor(test_pdf)
            
            # Get PDF info
            print('\n3. Getting PDF info:')
            pdf_info = extractor.get_pdf_info()
            print(json.dumps(pdf_info, indent=2, default=str))
            
            # Extract using all methods (limited for testing)
            print('\n4. Running extraction (Camelot + EasyOCR only):')
            
            # Test Camelot
            tables_camelot = extractor.extract_tables_camelot('lattice')
            print(f"   Camelot found: {len(tables_camelot)} tables")
            
            # Test EasyOCR
            images = extractor.extract_images_for_ocr()
            tables_ocr = extractor.extract_with_ocr_easyocr(images)
            print(f"   EasyOCR found: {len(tables_ocr)} tables")
            
            # Show results
            all_tables = tables_camelot + tables_ocr
            print(f'\n5. Results Summary:')
            print(f"   Total tables found: {len(all_tables)}")
            
            for i, table in enumerate(all_tables, 1):
                method = getattr(table, 'attrs', {}).get('method', 'unknown')
                confidence = getattr(table, 'attrs', {}).get('confidence', 0.0)
                print(f"   Table {i}: {table.shape} - {method} (conf: {confidence:.2f})")
                
                # Show preview
                print(f"   Preview (first 3 rows):")
                preview = table.head(3)
                print("   " + str(preview).replace('\n', '\n   '))
                print("   " + "-" * 40)
            
            # Save best table
            if all_tables:
                best_table = all_tables[0]
                csv_path = "mcp_test_extracted_table.csv"
                best_table.to_csv(csv_path, index=False)
                print(f"\n💾 Saved best table to: {csv_path}")
                print(f"   Shape: {best_table.shape}")
            
            print(f"\n✅ Direct extraction test completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print("❌ No PDF files found in current directory")
        print("Available files:")
        for file in os.listdir('.'):
            print(f"   {file}")

if __name__ == "__main__":
    test_pdf_extraction_directly()
