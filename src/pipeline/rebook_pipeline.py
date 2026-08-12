#!/usr/bin/env python3
"""
ReBook Production Pipeline (核心生产管线)
========================================
设计哲学：分层协作 (Tiered Orchestration)
  Tier 1 - 蓝领层: PDF 切页 + OCR 粗提 (本地/轻量)
  Tier 2 - 主编层: LLM 语义修复 + 双语重塑 + 知识萃取 (可配置任意模型)
  Tier 3 - 装配层: 输出 Markdown / HTML / EPUB / PDF / 可执行 App

用法:
  python rebook_pipeline.py --pdf <你的书.pdf> --pages 1-30 [--model economy|flagship]
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# ============ Tier 1: 蓝领层 (PDF → 图片 → 文本) ============

def extract_pdf_pages(pdf_path: str, start: int, end: int, output_dir: Path) -> list[Path]:
    """使用 PyMuPDF 将指定页码范围转为高清图片"""
    import fitz
    output_dir.mkdir(parents=True, exist_ok=True)
    images = []
    
    doc = fitz.open(pdf_path)
    for page_num in range(start, min(end, len(doc))):
        page = doc.load_page(page_num)
        # 2x 缩放保证 OCR 精度
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_path = output_dir / f"page_{page_num+1:04d}.png"
        pix.save(str(img_path))
        images.append(img_path)
    doc.close()
    print(f"📄 蓝领层: 已切出 {len(images)} 页图片 → {output_dir}")
    return images


def local_ocr(image_path: Path, lang: str = "chi_sim+eng") -> str:
    """本地 Tesseract 兜底 OCR（当不调用视觉模型时的免费方案）"""
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(image_path), lang=lang)
    except ImportError:
        print("⚠️ 未安装 pytesseract，将依赖外部视觉模型")
        return ""


# ============ Tier 2: 主编层 (LLM 修复 + 重塑 + 萃取) ============

def call_llm(system_prompt: str, user_content: str, model: str = "auto") -> str:
    """
    统一的大模型调用接口（核心切换点！）
    
    设计: 我们支持任意 OpenAI 兼容接口的模型供应商
    通过环境变量切换:
      LLM_PROVIDER = openai | deepseek | qwen | glm | anthropic
      LLM_MODEL    = 具体的模型名
      LLM_API_KEY  = 你的密钥
    
    在"蓝领层"可以切换为经济型模型 (如 deepseek-chat / gpt-4o-mini)
    在"主编层"可以切换为旗舰模型 (如 gpt-4o / claude-3.5-sonnet)
    """
    provider = os.getenv("LLM_PROVIDER", "openai")
    model_name = os.getenv("LLM_MODEL", model)
    api_key = os.getenv("LLM_API_KEY", "")
    
    if not api_key:
        raise ValueError("❌ 缺少 LLM_API_KEY 环境变量！请配置你的 API 密钥")
    
    # OpenAI 兼容接口 (覆盖 deepseek/qwen/glm 等大多数国内模型)
    if provider in ("openai", "deepseek", "qwen", "glm"):
        from openai import OpenAI
        base_url = {
            "openai": None,
            "deepseek": "https://api.deepseek.com",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "glm": "https://open.bigmodel.cn/api/paas/v4",
        }.get(provider)
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
        )
        return resp.choices[0].message.content
    
    elif provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model_name,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return resp.content[0].text
    
    raise ValueError(f"未知的模型供应商: {provider}")


def load_prompt(name: str) -> str:
    """从 docs/PROMPTS.md 中按需加载对应层级的 Prompt"""
    prompts_path = Path(__file__).parent.parent.parent / "docs" / "PROMPTS.md"
    content = prompts_path.read_text(encoding="utf-8")
    # 简单的按段落标记切分（正式版可改为结构化 YAML）
    markers = {
        "healer": "Prompt 1: The Healer",
        "architect": "Filter EN-Biopic",
        "extractor": "知识拓展榨汁机",
    }
    for key, marker in markers.items():
        if marker in content:
            return marker
    return content


async def process_page(text: str, mode: str = "standard") -> dict:
    """
    单页处理: 修复 → 双语 → 知识卡
    mode = standard (客观基准) | isaacson (传记推荐) | hanhan | hemingway
    """
    system_prompt = load_prompt("architect") if mode == "isaacson" else load_prompt("healer")
    
    # 阶段1: 语义修复 (Healer)
    fixed = call_llm(system_prompt, text, model=os.getenv("ECON_MODEL", "gpt-4o-mini"))
    
    # 阶段2: 双语重塑 (Architect)
    bilingual = call_llm(
        f"你是《史蒂夫·乔布斯传》作者沃尔特·艾萨克森。将以下中文重塑为地道现代商业英语: {fixed}",
        fixed,
        model=os.getenv("FLAGSHIP_MODEL", "gpt-4o"),
    )
    
    # 阶段3: 知识萃取 (Extractor)
    cheat = call_llm(
        "你是商学院教授。提取3-5个高阶商业词汇并造句，标注精彩修辞与背景知识。",
        bilingual,
        model=os.getenv("ECON_MODEL", "gpt-4o-mini"),
    )
    
    return {"fixed": fixed, "bilingual": bilingual, "cheat_sheet": cheat}


# ============ Tier 3: 装配层 (输出多端格式) ============

def assemble_markdown(results: list[dict]) -> str:
    """把全部处理结果拼装为结构化 Markdown"""
    md = ["# ReBook 重制输出\n"]
    for i, r in enumerate(results, 1):
        md.append(f"\n---\n\n## 段落 {i}\n")
        md.append(r["fixed"] + "\n")
        md.append(r["bilingual"] + "\n")
        md.append(r["cheat_sheet"] + "\n")
    return "\n".join(md)


def build_html(markdown_text: str, title: str = "ReBook") -> Path:
    """调用模板引擎生成交互式 HTML（含 Alpine.js 知识侧边栏）"""
    import subprocess
    # 调用 Node 渲染脚本（在 template_engine/ 中）
    script = r"""
const ejs = require('ejs');
const md = require('markdown-it')();
const fs = require('fs');

const template = fs.readFileSync('src/templates/template.ejs', 'utf8');
const body = md.render(fs.readFileSync(process.argv[2], 'utf8'));
const html = ejs.render(template, { title: process.argv[3], body_content: body, current_mode: 'The Isaacson Mode' });
fs.writeFileSync('output/book.html', html);
console.log('✅ HTML 已生成: output/book.html');
"""
    Path("output").mkdir(exist_ok=True)
    md_file = Path("output/book.md")
    md_file.write_text(markdown_text, encoding="utf-8")
    
    subprocess.run(["node", "-e", script, str(md_file), title], check=True)
    return Path("output/book.html")


def build_epub(markdown_text: str) -> Path:
    """Pandoc 一键封装 EPUB（Kindle / Apple Books 兼容）"""
    import subprocess
    md_file = Path("output/book.md")
    md_file.write_text(markdown_text, encoding="utf-8")
    subprocess.run(["pandoc", str(md_file), "-o", "output/book.epub", "--toc"], check=True)
    print("📖 EPUB 已生成: output/book.epub")
    return Path("output/book.epub")


# ============ 主入口 ============

def main():
    parser = argparse.ArgumentParser(description="ReBook 生产管线")
    parser.add_argument("--pdf", required=True, help="输入 PDF 路径")
    parser.add_argument("--pages", default="1-10", help="页码范围, 如 1-50")
    parser.add_argument("--mode", default="isaacson", choices=["standard", "isaacson", "hanhan", "hemingway"])
    parser.add_argument("--formats", default="md,html", help="输出格式: md,html,epub")
    args = parser.parse_args()
    
    start, end = map(int, args.pages.split("-"))
    
    print("🚀 ReBook 生产管线启动")
    print(f"   输入: {args.pdf}")
    print(f"   范围: 第 {start}-{end} 页 | 风格: {args.mode}")
    
    # Tier 1: 切页
    images = extract_pdf_pages(args.pdf, start-1, end, Path("workdir/pages"))
    
    # Tier 2: 每页 OCR + 主编处理
    results = []
    for img in images[:2]:  # MVP: 先处理前2页验证
        raw = local_ocr(img)
        if not raw.strip():
            print(f"⚠️ 第 {img.stem} 页 OCR 为空，跳过")
            continue
        result = asyncio.run(process_page(raw, args.mode))
        results.append(result)
        print(f"✅ 第 {img.stem} 页处理完成")
    
    # Tier 3: 装配输出
    markdown_text = assemble_markdown(results)
    
    for fmt in args.formats.split(","):
        if fmt == "md":
            Path("output/book.md").write_text(markdown_text, encoding="utf-8")
            print("📝 Markdown 已生成: output/book.md")
        elif fmt == "html":
            build_html(markdown_text)
        elif fmt == "epub":
            build_epub(markdown_text)
    
    print("\n🎉 管线完成！产出物在 output/ 目录")
    print("   💡 下一步: 用浏览器打开 output/book.html 体验交互式阅读")


if __name__ == "__main__":
    main()
