# 🚀 ReBook 快速上手 (Quick Start)

> **三分钟跑通"从泛黄扫描件到双语交互读物"的全流程。**

## 第一步：安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# Node 依赖 (HTML 渲染引擎)
npm install
```

## 第二步：配置你的模型密钥

```bash
# 复制配置模板
cp .env.example .env

# 用编辑器打开 .env，填入你的 API Key
# 支持: DeepSeek / OpenAI / 通义千问 / 智谱 / Claude
# 通过 LLM_PROVIDER 一行切换供应商
```

## 第三步：启动生产管线

```bash
# 处理《张忠谋自传上册》第 1-10 页, 使用艾萨克森文风
python src/pipeline/rebook_pipeline.py \
  --pdf "張忠謀自傳上冊(1931-1964).pdf" \
  --pages 1-10 \
  --mode isaacson \
  --formats md,html
```

## 第四步：收获成果

运行完成后，在 `output/` 目录下你会得到：

| 文件 | 用途 |
|------|------|
| `book.md` | 结构化双语资产 (纯数据) |
| `book.html` | 交互式阅读单页 (推荐!) |
| `book.epub` | Kindle / Apple Books 适配 |

## 🎯 个性化选项

### 切换文风滤镜 (Persona Filters)

```bash
--mode standard    # 客观中性基准线 (默认)
--mode isaacson    # 沃尔特·艾萨克森风 (传记推荐)
--mode hanhan      # 韩寒风 (中文再创作)
--mode hemingway   # 海明威极简风
```

### 切换模型层级 (Tiered Orchestration)

在 `.env` 中分别配置:
- `ECON_MODEL` = 蓝领层 (经济模型, 批量干活)
- `FLAGSHIP_MODEL` = 主编层 (旗舰模型, 核心创作)

**"让天才去创造，让劳模去搬砖。"**

## ❓ 常见问题

**Q: 没有 API Key 怎么办?**
A: 你可以先只用本地 OCR (Tesseract) 提取原文，后续再补 Key 做 AI 处理。

**Q: 处理几百页的书会很久吗?**
A: 蓝领层用经济模型批量跑，速度极快；主编层只处理关键段落。成本可控。
