"""
Extract tributary area content from Structural Engineering Reference Manual
"""
from PyPDF2 import PdfReader
import re

# Load PDF
pdf_path = "reference_manual.pdf"
reader = PdfReader(pdf_path)

print(f"Total pages: {len(reader.pages)}")

# Keywords to search for
keywords = ["tributary", "tributary area", "load distribution", "two-way slab", "one-way slab", 
            "45 degree", "beam reaction", "column load"]

# Search through all pages
found_content = []
for i, page in enumerate(reader.pages):
    try:
        text = page.extract_text()
        if text:
            text_lower = text.lower()
            for kw in keywords:
                if kw.lower() in text_lower:
                    # Clean text for output
                    clean_text = text.encode('ascii', 'ignore').decode('ascii')
                    found_content.append((i+1, kw, clean_text))
                    break
    except Exception as e:
        pass

print(f"\nFound {len(found_content)} pages with relevant content")

# Write to file instead of printing
with open("tributary_content_extracted.txt", "w", encoding="utf-8") as f:
    for pg, kw, content in found_content:
        f.write(f"\n{'='*60}\n")
        f.write(f"PAGE {pg} - Keyword: '{kw}'\n")
        f.write(f"{'='*60}\n")
        f.write(content[:3000])
        f.write("\n\n")

print("Content saved to tributary_content_extracted.txt")
