#!/usr/bin/env python3
"""
MCP PDF Tool - FastMCP Implementation
Creates an MCP server for PDF table extraction using multiple methods
"""

from fastmcp import FastMCP
from typing import Dict, List, Optional, Union
import os
import json
from pathlib import Path

# Import our comprehensive extractor
from mcp_comprehensive_extractor import MCPPDFTableExtractor

# Initialize FastMCP server
mcp = FastMCP("PDF Table Extractor")

@mcp.tool()
def extract_pdf_content(file_path: str, extraction_method: str = "all") -> Dict:
    """
    Extract text and tables from PDF files using multiple methods
    
    Args:
        file_path: Path to the PDF file
        extraction_method: Method to use - 'camelot', 'tabula', 'ocr', 'all'
    
    Returns:
        Dictionary containing extraction results
    """
    
    # Validate file path
    pdf_path = Path(file_path)
    if not pdf_path.exists():
        return {
            "error": f"PDF file not found: {file_path}",
            "success": False
        }
    
    if not pdf_path.suffix.lower() == '.pdf':
        return {
            "error": f"File is not a PDF: {file_path}",
            "success": False
        }
    
    try:
        # Initialize extractor
        extractor = MCPPDFTableExtractor(str(pdf_path))
        
        if extraction_method == "all":
            # Run comprehensive extraction
            results = extractor.extract_all_methods()
            
            # Format for MCP response
            response = {
                "success": True,
                "pdf_info": results['pdf_info'],
                "tables_found": len(results['best_tables']),
                "extraction_methods": {
                    method: len(tables) for method, tables in results['extraction_methods'].items()
                },
                "best_tables": []
            }
            
            # Add table previews
            for i, table in enumerate(results['best_tables'], 1):
                table_info = {
                    "table_index": i,
                    "shape": table.shape,
                    "columns": list(table.columns),
                    "preview": table.head(3).to_dict('records'),
                    "method": getattr(table, 'attrs', {}).get('method', 'unknown'),
                    "confidence": getattr(table, 'attrs', {}).get('confidence', 0.0)
                }
                response["best_tables"].append(table_info)
            
            return response
            
        elif extraction_method == "camelot":
            tables = extractor.extract_tables_camelot('lattice')
            return {
                "success": True,
                "method": "camelot",
                "tables_found": len(tables),
                "tables": [{"shape": t.shape, "preview": t.head(3).to_dict('records')} for t in tables]
            }
            
        elif extraction_method == "tabula":
            tables = extractor.extract_tables_tabula()
            return {
                "success": True,
                "method": "tabula", 
                "tables_found": len(tables),
                "tables": [{"shape": t.shape, "preview": t.head(3).to_dict('records')} for t in tables]
            }
            
        elif extraction_method == "ocr":
            images = extractor.extract_images_for_ocr()
            tables = extractor.extract_with_ocr_easyocr(images)
            return {
                "success": True,
                "method": "ocr",
                "tables_found": len(tables),
                "tables": [{"shape": t.shape, "preview": t.head(3).to_dict('records')} for t in tables]
            }
            
        else:
            return {
                "error": f"Unknown extraction method: {extraction_method}",
                "success": False,
                "available_methods": ["all", "camelot", "tabula", "ocr"]
            }
    
    except Exception as e:
        return {
            "error": f"Extraction failed: {str(e)}",
            "success": False
        }

@mcp.tool()
def get_pdf_info(file_path: str) -> Dict:
    """
    Get basic information about a PDF file
    
    Args:
        file_path: Path to the PDF file
    
    Returns:
        Dictionary with PDF metadata and basic info
    """
    
    pdf_path = Path(file_path)
    if not pdf_path.exists():
        return {
            "error": f"PDF file not found: {file_path}",
            "success": False
        }
    
    try:
        extractor = MCPPDFTableExtractor(str(pdf_path))
        info = extractor.get_pdf_info()
        info["success"] = True
        return info
    
    except Exception as e:
        return {
            "error": f"Failed to get PDF info: {str(e)}",
            "success": False
        }

@mcp.tool()
def extract_text_only(file_path: str) -> Dict:
    """
    Extract only text content from PDF (no tables)
    
    Args:
        file_path: Path to the PDF file
    
    Returns:
        Dictionary containing extracted text
    """
    
    pdf_path = Path(file_path)
    if not pdf_path.exists():
        return {
            "error": f"PDF file not found: {file_path}",
            "success": False
        }
    
    try:
        extractor = MCPPDFTableExtractor(str(pdf_path))
        text = extractor.extract_text_pymupdf()
        
        return {
            "success": True,
            "text": text,
            "character_count": len(text),
            "method": "pymupdf"
        }
    
    except Exception as e:
        return {
            "error": f"Text extraction failed: {str(e)}",
            "success": False
        }

@mcp.tool()
def list_available_pdfs(directory_path: str = ".") -> Dict:
    """
    List all PDF files in a directory
    
    Args:
        directory_path: Directory to search for PDFs (default: current directory)
    
    Returns:
        Dictionary with list of PDF files
    """
    
    try:
        dir_path = Path(directory_path)
        if not dir_path.exists():
            return {
                "error": f"Directory not found: {directory_path}",
                "success": False
            }
        
        pdf_files = []
        for file_path in dir_path.glob("*.pdf"):
            file_info = {
                "filename": file_path.name,
                "path": str(file_path),
                "size": file_path.stat().st_size
            }
            pdf_files.append(file_info)
        
        return {
            "success": True,
            "directory": str(dir_path),
            "pdf_count": len(pdf_files),
            "pdf_files": pdf_files
        }
    
    except Exception as e:
        return {
            "error": f"Failed to list PDFs: {str(e)}",
            "success": False
        }

@mcp.tool()
def save_table_to_csv(file_path: str, table_index: int = 1, output_path: Optional[str] = None) -> Dict:
    """
    Extract a specific table and save it as CSV
    
    Args:
        file_path: Path to the PDF file
        table_index: Index of the table to save (1-based)
        output_path: Output CSV path (optional, auto-generated if not provided)
    
    Returns:
        Dictionary with save operation results
    """
    
    try:
        # Extract tables
        extractor = MCPPDFTableExtractor(file_path)
        results = extractor.extract_all_methods()
        
        if len(results['best_tables']) < table_index:
            return {
                "error": f"Table {table_index} not found. Only {len(results['best_tables'])} tables available.",
                "success": False
            }
        
        # Get the requested table
        table = results['best_tables'][table_index - 1]
        
        # Generate output path if not provided
        if output_path is None:
            pdf_name = Path(file_path).stem
            output_path = f"{pdf_name}_table_{table_index}.csv"
        
        # Save table
        table.to_csv(output_path, index=False)
        
        return {
            "success": True,
            "output_path": output_path,
            "table_shape": table.shape,
            "method": getattr(table, 'attrs', {}).get('method', 'unknown')
        }
    
    except Exception as e:
        return {
            "error": f"Failed to save table: {str(e)}",
            "success": False
        }

if __name__ == "__main__":
    print("🚀 Starting MCP PDF Table Extractor Server...")
    print("📄 Available tools:")
    print("   • extract_pdf_content - Comprehensive PDF table extraction")
    print("   • get_pdf_info - Get PDF metadata and basic information")
    print("   • extract_text_only - Extract text content only")
    print("   • list_available_pdfs - List PDF files in directory")
    print("   • save_table_to_csv - Save specific table as CSV")
    print("\n🔧 Server ready for MCP connections...")
    
    # Run the MCP server
    mcp.run()
