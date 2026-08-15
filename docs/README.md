# ReadShift 专题技术与设计规范索引 (Technical & Design Documentation Index)

> **定位**：本目录（`docs/`）汇集了 ReadShift 项目在架构设计、提示词工程、排版美学、经验教训与健康检测方面的深入专题文档。  
> **统筹原则**：全局概览与产品发心以根目录 `README.md` 为准；全流程执行标准与质量门禁以根目录 `执行手册.md` 为准。

---

## 📚 专题文档导航矩阵

| 文档名称 | 核心内容与职责 | 关键受众 / 触发场景 |
| :--- | :--- | :--- |
| **[`QUICKSTART.md`](./QUICKSTART.md)** | **3 分钟快速上手**：环境安装、API 密钥配置与 4 大核心指令（编译/QA/管线/EPUB） | 新用户、接手开发者快速跑通流水线 |
| **[`ARCHITECTURE_AND_METHODOLOGY.md`](./ARCHITECTURE_AND_METHODOLOGY.md)** | **系统架构与方法论**：“二生万物”多模态哲学、三层数据隔离模型、大小模型分层协作机制 | 系统架构师、理解系统整体设计者 |
| **[`DESIGN_PLAN.md`](./DESIGN_PLAN.md)** | **排版美学与设计规范**：Tschichold 比例法则、墨页色彩体系、首字下沉与 EPUB 防撕裂规则 | UI 设计师、排版工程师、前端渲染 |
| **[`PROMPTS.md`](./PROMPTS.md)** | **Prompt 矩阵**：客观基准线与艾萨克森（传记）、韩寒、余秋雨、海明威风格化 DLC 库 | 大模型双语重塑、提示词调优 |
| **[`LESSONS_LEARNED.md`](./LESSONS_LEARNED.md)** | **踩坑经验总库**：EPUB XML 解析崩溃、双页对开死黑、数据双写分叉与 QA 误判等血泪教训 | 所有 Agent 与开发者开工前必读 |
| **[`HANDOFF_FULLBOOK_20260813.md`](./HANDOFF_FULLBOOK_20260813.md)** | **全书合成交接手册**：多章聚合、锚点裁剪与 HTML 全量成书的收尾工作记录 | 全书合成与多章交接审查 |
| **[`HEALTHCHECK.sh`](./HEALTHCHECK.sh)** | **源料体检脚本**：自动化检测 `source/*.md` 中的未闭合标签、占位符、多空行与孤立标题 | 生产 Agent 每次动笔前的第一道防线 |
