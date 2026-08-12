"""《张忠谋自传》前15页 OCR 质量体检 —— 多进程并行版"""
import fitz, re, subprocess, os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

pdf_path = "張忠謀自傳上冊(1931-1964).pdf"
PAGES = 15
workdir = Path("workdir/quality_check")
workdir.mkdir(parents=True, exist_ok=True)
ocr_dir = workdir / "ocr_full"
ocr_dir.mkdir(exist_ok=True)

def extract_and_ocr(page_num):
    """单个 worker: 切页 + OCR"""
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    img_path = workdir / f"page_{page_num+1:03d}.png"
    pix.save(str(img_path))
    doc.close()
    
    result = subprocess.run(
        ['tesseract', str(img_path), 'stdout', '-l', 'chi_sim+eng', '--psm', '3'],
        capture_output=True, text=True
    )
    text = result.stdout
    (ocr_dir / f"page_{page_num+1:03d}.txt").write_text(text, encoding='utf-8')
    
    char_count = len(re.sub(r'\s', '', text))
    space_ratio = text.count(' ') / max(len(text), 1)
    sample = text[:120].replace('\n', ' ')
    return {'page': page_num+1, 'char_count': char_count, 'space_ratio': space_ratio, 'sample': sample}

if __name__ == '__main__':
    print(f"🚀 并行启动: {PAGES} 页 OCR (CPU 核心数: {multiprocessing.cpu_count()})")
    results = []
    
    with ProcessPoolExecutor(max_workers=min(PAGES, multiprocessing.cpu_count())) as executor:
        futures = {executor.submit(extract_and_ocr, i): i for i in range(PAGES)}
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            print(f"  ✅ 第{r['page']:2d}页: {r['char_count']:5d} 字, 空格占比 {r['space_ratio']*100:5.1f}%", flush=True)
    
    results.sort(key=lambda x: x['page'])
    
    print("\n" + "="*70)
    print("📊 前15页质量诊断报告")
    print("="*70)
    
    avg_chars = sum(r['char_count'] for r in results) / len(results)
    high_space_pages = [r['page'] for r in results if r['space_ratio'] > 0.25]
    low_content_pages = [r['page'] for r in results if r['char_count'] < 50]
    
    print(f"\n📈 平均每页有效字符: {avg_chars:.0f} 字")
    print(f"⚠️  空格占比过高 (>25%) 的页面: {high_space_pages or '无'}")
    print(f"⚠️  内容过少 (<50字, 可能是空白页/插图页) 的页面: {low_content_pages or '无'}")
    
    print("\n🔍 页面类型初步判断 (前12页):")
    page_type_kws = {
        '封面/扉页': ['張忠謀', '自傳', 'Morris', '回忆', '懷'],
        '目录/序': ['目錄', '目录', 'Contents', '序', '前言'],
        '版权/出版信息': ['出版', '版權', 'Copyright', 'ISBN', '印刷'],
    }
    for r in results[:12]:
        ptype = '正文'
        for t, kws in page_type_kws.items():
            if any(kw in r['sample'] for kw in kws):
                ptype = t
                break
        print(f"  第{r['page']:2d}页 → {ptype} | 样例: {r['sample'][:60]}")
    
    print("\n💾 全部 OCR 结果已保存: workdir/quality_check/ocr_full/page_001.txt ~ page_015.txt")
