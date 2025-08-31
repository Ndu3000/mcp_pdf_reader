#!/usr/bin/env python3
"""
Test script for MCP PDF Tool
"""

from mcp_pdf_tool import extract_pdf_content, get_pdf_info, list_available_pdfs
import json

def test_mcp_pdf_tool():
    """Test the MCP PDF tool functions"""
    
    print('📄 Testing MCP PDF Tool')
    print('=' * 50)

    # Test 1: List available PDFs
    print('\n1. Listing available PDFs:')
    result = list_available_pdfs('.')
    print(json.dumps(result, indent=2))

    # Test 2: Get PDF info
    print('\n2. Getting PDF info:')
    result = get_pdf_info('test.pdf')
    print(json.dumps(result, indent=2))

    # Test 3: Extract PDF content with all methods
    print('\n3. Extracting PDF content (all methods):')
    result = extract_pdf_content('test.pdf', 'all')
    print('Tables found:', result.get('tables_found', 0))
    print('Methods used:', result.get('extraction_methods', {}))
    print('Success:', result.get('success', False))
    
    if result.get('success'):
        print('\n📊 Best Tables Summary:')
        for table in result.get('best_tables', []):
            print(f"   Table {table['table_index']}: {table['shape']} - {table['method']}")

if __name__ == "__main__":
    test_mcp_pdf_tool()
