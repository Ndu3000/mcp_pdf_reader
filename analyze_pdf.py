"""
Direct PDF reader using PyMuPDF to analyze the actual content
"""

import fitz  # PyMuPDF
import json

def read_pdf_content(pdf_path: str):
    """Read and analyze PDF content using PyMuPDF"""
    
    print(f"🔍 Analyzing PDF: {pdf_path}")
    print("=" * 60)
    
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        print(f"📄 Document Info:")
        print(f"   Pages: {doc.page_count}")
        print(f"   Title: {doc.metadata.get('title', 'N/A')}")
        print(f"   Author: {doc.metadata.get('author', 'N/A')}")
        print(f"   Creator: {doc.metadata.get('creator', 'N/A')}")
        print(f"   Producer: {doc.metadata.get('producer', 'N/A')}")
        
        # Analyze each page
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            print(f"\n📃 PAGE {page_num + 1}:")
            print(f"   Size: {page.rect.width:.1f} x {page.rect.height:.1f}")
            
            # Get text content
            text = page.get_text("text")
            print(f"   Text length: {len(text)} characters")
            
            # Get text blocks
            text_blocks = page.get_text("blocks")
            print(f"   Text blocks: {len(text_blocks)}")
            
            # Get structured text (words with positions)
            text_dict = page.get_text("dict")
            print(f"   Text dictionary blocks: {len(text_dict.get('blocks', []))}")
            
            # Try to detect tables by looking for structured layout
            lines = page.get_text("text").split('\n')
            potential_table_lines = []
            
            for line in lines:
                line = line.strip()
                if line:
                    # Count spaces/tabs to detect columnar data
                    spaces = line.count('  ')  # Multiple spaces might indicate columns
                    tabs = line.count('\t')
                    if spaces > 2 or tabs > 0:
                        potential_table_lines.append(line)
            
            print(f"   Potential table lines: {len(potential_table_lines)}")
            
            # Show first few lines of text for inspection
            print(f"\n   📝 First 10 lines of text:")
            lines = text.split('\n')[:10]
            for i, line in enumerate(lines, 1):
                if line.strip():
                    print(f"      {i:2d}: {repr(line)}")
            
            # Show potential table lines
            if potential_table_lines:
                print(f"\n   📊 Potential table content (first 5 lines):")
                for i, line in enumerate(potential_table_lines[:5], 1):
                    print(f"      {i:2d}: {repr(line)}")
            
            # Get images
            image_list = page.get_images()
            print(f"   Images: {len(image_list)}")
            
            # Get drawings (lines, shapes)
            drawings = page.get_drawings()
            print(f"   Drawings/shapes: {len(drawings)}")
            
        # Extract all text and save to file for detailed analysis
        all_text = ""
        for page_num in range(doc.page_count):
            page = doc[page_num]
            all_text += f"\n\n=== PAGE {page_num + 1} ===\n\n"
            all_text += page.get_text("text")
        
        # Save full text
        with open("pdf_raw_text.txt", "w", encoding="utf-8") as f:
            f.write(all_text)
        
        print(f"\n💾 Full PDF text saved to: pdf_raw_text.txt")
        
        # Try to extract with different modes
        print(f"\n🔬 Trying different extraction modes:")
        
        for page_num in range(min(1, doc.page_count)):  # Just first page
            page = doc[page_num]
            
            # HTML mode
            html_text = page.get_text("html")
            print(f"   HTML extraction: {len(html_text)} chars")
            
            # XML mode  
            xml_text = page.get_text("xml")
            print(f"   XML extraction: {len(xml_text)} chars")
            
            # XHTML mode
            xhtml_text = page.get_text("xhtml")
            print(f"   XHTML extraction: {len(xhtml_text)} chars")
            
            # Save HTML for analysis
            with open("pdf_html_extract.html", "w", encoding="utf-8") as f:
                f.write(html_text)
            print(f"   HTML extraction saved to: pdf_html_extract.html")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")

def main():
    pdf_path = "../test.pdf"  # Relative to mcp_pdf_reader directory
    read_pdf_content(pdf_path)

if __name__ == "__main__":
    main()
