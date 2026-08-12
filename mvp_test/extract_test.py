import fitz  # PyMuPDF
import sys
import os

pdf_path = "../張忠謀自傳上冊(1931-1964).pdf"
page_num = 14  # 盲猜第 14 页可能是正文开始的某一页

try:
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    
    # 将该页转为图片 (提升一点分辨率)
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    img_path = "page_test.png"
    pix.save(img_path)
    print(f"Successfully extracted page {page_num} to {img_path}")
    
except Exception as e:
    print(f"Error handling PDF: {e}")
    sys.exit(1)
