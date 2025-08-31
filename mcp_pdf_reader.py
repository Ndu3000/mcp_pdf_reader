from dataclasses import dataclass
from typing import AsyncIterator
from mcp.server.fastmcp import FastMCP
import fitz  # correct import for PyMuPDF
import os
import sys
import argparse
from contextlib import asynccontextmanager

# Directory where PDFs are stored
PDF_DIRECTORY = os.getenv("PDF_DIRECTORY", "./pdfs")

@dataclass
class AppContext:
    """Application context for lifecycle management."""
    pdf_directory: str

# Initialize the MCP server (lifespan added below)
mcp = FastMCP("PDF Reader")

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    try:
        # Setup can go here
        yield AppContext(pdf_directory=PDF_DIRECTORY)
    finally:
        # Cleanup (if needed)
        pass

# Assign lifespan to server
mcp.lifespan = app_lifespan

@mcp.tool()
def read_pdf(ctx, filename: str) -> str:
    """
    Reads and extracts text from a specified PDF file.
    :param ctx: FastMCP context
    :param filename: Name of the PDF file to read
    :return: Extracted text from the PDF
    """
    pdf_path = os.path.join(PDF_DIRECTORY, filename)

    if not os.path.exists(pdf_path):
        return f"Error: File '{filename}' not found."

    try:
        # Open and extract text from the PDF
        doc = fitz.open(pdf_path)
        text = "\n".join([page.get_text("text") for page in doc])
        return text if text else "No text found in the PDF."
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def scan_pdf(filename: str) -> str:
    """
    Standalone function to scan and extract text from a PDF file.
    :param filename: Path to the PDF file to scan
    :return: Extracted text from the PDF
    """
    # Check if file exists
    if not os.path.exists(filename):
        return f"Error: File '{filename}' not found."
    
    try:
        # Open and extract text from the PDF
        doc = fitz.open(filename)
        text = "\n".join([page.get_text("text") for page in doc])
        doc.close()
        return text if text else "No text found in the PDF."
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def llama_scan_cli():
    """
    Command-line interface for llama-scan command.
    """
    parser = argparse.ArgumentParser(
        description="Scan and extract text from PDF files",
        prog="llama-scan"
    )
    parser.add_argument(
        "filename", 
        help="PDF file to scan"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file to save extracted text (optional, prints to stdout by default)"
    )
    
    args = parser.parse_args()
    
    # Scan the PDF
    result = scan_pdf(args.filename)
    
    # Output the result
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"Text extracted and saved to: {args.output}")
        except Exception as e:
            print(f"Error writing to output file: {str(e)}", file=sys.stderr)
            sys.exit(1)
    else:
        print(result)

# Run the MCP server
def main():
    mcp.run()

if __name__ == "__main__":
    main()
