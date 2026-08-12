import pytesseract
from PIL import Image
import sys

img_path = "page_test.png"

try:
    print("由于系统目前只有 chi_sim，我们使用 'chi_sim+eng' 进行强行提取...\n这正是最残缺的原始形态：")
    text = pytesseract.image_to_string(Image.open(img_path), lang='chi_sim+eng')
    
    print("\n--- 提取出的原始文本 (前500字) ---")
    print(text[:500])
    print("---------------------------------\n")
    
    with open("raw_text.txt", "w", encoding="utf-8") as f:
        f.write(text)
        print("完整残缺结果已保存至 raw_text.txt - 等待高阶主编的洗礼")

except Exception as e:
    print(f"OCR 提取失败: {e}")
