/**
 * ReadShift HTML 渲染器 v9 (杂志级阅读体验)
 * - 双语段落流式排版（无表格），中文衬线 + 英文无衬线，首段 Drop Cap
 * - 知识卡片（Cheat Sheet）精致三栏布局
 * - 书眉 / 扉页 / 页脚装饰体系
 * - interactive-term 词卡可点击弹出知识窗
 */

const ejs = require('ejs');
const MarkdownIt = require('markdown-it');
const fs = require('fs');
const path = require('path');

const md = new MarkdownIt({ html: true, linkify: true, typographer: true });
const templatePath = path.join(__dirname, '..', 'src', 'templates', 'template.ejs');
const template = fs.readFileSync(templatePath, 'utf8');




// ── 命令行参数：--page-range "2-45" 只渲染指定页码范围；--out 指定输出文件 ──
const args = process.argv.slice(2);
function argVal(name, def) {
    const i = args.indexOf(name);
    return i >= 0 && args[i + 1] ? args[i + 1] : def;
}
const pageRangeArg = argVal('--page-range', '');
const outFileArg = argVal('--out', '');
const chapterArg = argVal('--chapter', '');
const chaptersArg = argVal('--chapters', ''); // 多章合成：逗号分隔章号，如 --chapters 1,2,3
const fullDirArg = argVal('--full-dir', '') || argVal('--input', '');
let fullDir = fullDirArg ? path.resolve(process.cwd(), fullDirArg) : path.join(__dirname, '..', 'output', 'full');
let outPath = outFileArg
    ? path.resolve(process.cwd(), outFileArg)
    : path.join(__dirname, '..', 'output', 'preview_book.html');

const chaptersDir = path.join(__dirname, '..', 'output', 'chapters');
// 多章合成模式：聚合多个章的 source 目录，按页码排序
let multiChapter = false;
let files = [];
if (chaptersArg) {
    multiChapter = true;
    const chNums = chaptersArg.split(',').map(s => s.trim()).filter(Boolean);
    for (const cn of chNums) {
        const chNum = cn.padStart(2, '0');
        const found = fs.existsSync(chaptersDir)
            ? fs.readdirSync(chaptersDir).find(d => d.startsWith(`chap-${chNum}-`))
            : null;
        if (found) {
            const srcDir = path.join(chaptersDir, found, 'source');
            fs.readdirSync(srcDir).filter(f => f.endsWith('.md') && f !== '_INDEX.md')
              .forEach(f => files.push(path.join(srcDir, f)));
        }
    }
    files.sort((a, b) => {
        const pa = parseInt((path.basename(a).match(/page_(\d+)/) || [0, 0])[1]) || 0;
        const pb = parseInt((path.basename(b).match(/page_(\d+)/) || [0, 0])[1]) || 0;
        return pa - pb;
    });
    if (!outFileArg) {
        const samplesDir = path.join(__dirname, '..', 'output', 'Samples');
        if (!fs.existsSync(samplesDir)) fs.mkdirSync(samplesDir, { recursive: true });
        const cnNums = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十'];
        const parts = chaptersArg.split(',').map(s => s.trim()).filter(Boolean);
        const first = parseInt(parts[0]) || 1;
        const last = parseInt(parts[parts.length - 1]) || parts.length;
        const rangeLabel = first === last ? cnNums[first] : `${cnNums[first]}-${cnNums[last]}`;
        outPath = path.join(samplesDir, `${rangeLabel}章合成-Chapter-${first}-${last}.html`);
    }
} else {
    if (chapterArg) {
        const chNum = chapterArg.padStart(2, '0');
        if (fs.existsSync(chaptersDir)) {
            const found = fs.readdirSync(chaptersDir).find(d => d.startsWith(`chap-${chNum}-`));
            if (found) {
                fullDir = path.join(chaptersDir, found, 'source');
                if (!outFileArg) {
                    const cnNums = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九'];
                    const numStr = cnNums[parseInt(chapterArg)] || chapterArg;
                    // 附录章使用权威命名（project.json 规定）
                    const isAppendix = found.includes('附录');
                    const htmlName = isAppendix ? '附录-Appendix.html' : `第${numStr}章-Chapter-${chapterArg}.html`;
                    outPath = path.join(chaptersDir, found, htmlName);
                }
            }
        }
    }
    files = fs.readdirSync(fullDir).filter(f => f.endsWith('.md') && f !== '_INDEX.md').sort()
        .map(f => path.join(fullDir, f));
}

let pageFilter = null;
if (pageRangeArg) {
    const m = pageRangeArg.match(/^(\d+)\s*-\s*(\d+)$/);
    if (m) {
        const lo = parseInt(m[1]), hi = parseInt(m[2]);
        pageFilter = (pn) => pn >= lo && pn <= hi;
    } else {
        const single = parseInt(pageRangeArg);
        if (!isNaN(single)) pageFilter = (pn) => pn === single;
    }
}

// ═══ 小节标题收集（生成两级目录用） ═══
let subsectionSeq = 0;
const subsections = [];      // { id, zh, en, chapterStart, page }
let currentChapterStart = 0; // 当前处理文件所属章节起始页

// ═══ 章节映射：页码 → 章节归属（基于原书物理页码） ═══
const CHAPTER_MAP = [
    { start: 1,  name: '序',           type: 'front' },
    { start: 7,  name: '推荐序一 · 为历史留下记录', type: 'front', by: '余秋雨 撰' },
    { start: 12, name: '推荐序二 · 出版企业家传记与回忆录的用心', type: 'front', by: '高希均 撰' },
    { start: 14, name: '作者自序 · 那是一个多么不同的时代！', type: 'front', by: '张忠谋 自撰' },
    { start: 23, name: '第一章 · "大时代"中的幼少年', title_zh: '第一章 大时代中的幼少年', title_en: 'Childhood & Youth in a Great Era', type: 'chapter', by: '张忠谋 著' },
    { start: 46, name: '第二章 · 哈佛大学与麻省理工', title_zh: '第二章 哈佛大学与麻省理工', title_en: 'Harvard and MIT', type: 'chapter', by: '张忠谋 著' },
    { start: 64, name: '第三章 · 进入半导体业', title_zh: '第三章 进入半导体业', title_en: 'Entering the Semiconductor Industry', type: 'chapter', by: '张忠谋 著' },
    { start: 78, name: '第四章 · 初试啼声', title_zh: '第四章 初试啼声', title_en: 'First Signs of Promise', type: 'chapter', by: '张忠谋 著' },
    { start: 93, name: '第五章 · 重拎书包', title_zh: '第五章 重拎书包', title_en: 'Back to School', type: 'chapter', by: '张忠谋 著' },
    { start: 101, name: '附录 · 张忠谋大事年表', title_zh: '附录 张忠谋大事年表', title_en: 'A Chronology of Morris Chang', type: 'back', by: '张忠谋 著' },
];

function getChapterForPage(pageNum) {
    let current = CHAPTER_MAP[0];
    for (const ch of CHAPTER_MAP) {
        if (pageNum >= ch.start) current = ch;
        else break;
    }
    return current;
}

// 渲染章节导航条：仅在章节起始页显示大标题卡片，章节内部不重复显示标题条
function renderChapterNav(pageNum, isSectionStart) {
    if (!isSectionStart) return '';
    const ch = getChapterForPage(pageNum);
    const byline = ch.by ? `<span class="chapter-nav__byline">${ch.by}</span>` : '';
    const label = ch.type === 'front' ? '序言' : (ch.type === 'back' ? '附录' : '章节');
    // 中英双语文案：中文用 title_zh（章节全名），英文用 title_en（斜体副标题）
    const zhTitle = ch.title_zh || ch.name;
    const enTitle = ch.title_en || '';
    const enHtml = enTitle ? `<span class="chapter-nav__title-en">${enTitle}</span>` : '';
    return `<div class="chapter-nav chapter-nav--start" id="chap-${pageNum}">
        <span class="chapter-nav__badge">${label}</span>
        <h2 class="chapter-nav__title">${zhTitle}</h2>
        ${enHtml}
        <div class="chapter-nav__divider"><span class="chapter-nav__divider-orn">✦</span></div>
        ${byline}
    </div>`;
}

let totalTerms = 0;

// ─── 工具函数 ──────────────────────────────────────────────────────
function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function isChineseLine(line) {
    if (!line || line.trim() === '') return false;
    const t = line.trim();
    if (/^[\#\-\*\|>`\d]/.test(t)) return false;
    return /[\u4e00-\u9fff\u3400-\u4dbf]/.test(t);
}

function isEnglishLine(line) {
    if (!line || line.trim() === '') return false;
    const t = line.trim();
    if (/^[\#\-\*\|>`\d]/.test(t)) return false;
    // English: starts with letter, quote, ellipsis, or dash
    return /^[A-Za-z"'«»\-…]/.test(t);
}

function isCheatSheetHeader(line) {
    const t = (line || '').trim().toLowerCase();
    return /cheat\s*sheet|商业语汇提炼|地道商业表达|商业词汇卡片|商业语汇|商业词汇/.test(t);
}

function isRhetoricHeader(line) {
    const t = (line || '').trim().toLowerCase();
    return /修辞与逻辑赏析|修辞赏析|修辞与逻辑|语言与逻辑赏析|语言赏析/.test(t);
}

function isKnowledgeHeader(line) {
    const t = (line || '').trim().toLowerCase();
    return /外链知识窗|知识窗|背景知识延伸|背景知识/.test(t);
}

// ─── 提取词汇及释义 ─────────────────────────────────────────────
function extractTermDetails(content) {
    const details = {};
    const lines = content.split('\n');

    // Pattern A: numbered list with 中文解释/商业造句
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        const numMatch = line.match(/^(\d+)\.\s*\*\*(.+?)\*\*/);
        if (!numMatch) continue;
        const termText = numMatch[2].trim();
        if (termText.length > 80 || !termText) continue;
        let meaning = '';
        let sentence = '';
        let j = i + 1;
        while (j < lines.length) {
            const l = lines[j].trim();
            if (l === '' || l.startsWith('---') || /^#{1,3}\s/.test(l) || /^\d+\.\s+\*\*/.test(l)) break;
            const meanMatch = l.match(/^\*\*中文解释\*\*[：:]\s*(.+)$/);
            const sentMatch = l.match(/^\*\*商业造句\*\*[：:]\s*(.+)$/);
            if (meanMatch) meaning += (meaning ? ' ' : '') + meanMatch[1].trim();
            if (sentMatch) sentence += (sentence ? ' ' : '') + sentMatch[1].trim();
            j++;
        }
        if (meaning && termText.length < 80) {
            details[termText] = { meaning, sentence };
            const shortKey = termText.split('/')[0].trim().split(' /')[0].trim();
            if (shortKey && shortKey !== termText && !details[shortKey]) {
                details[shortKey] = { meaning, sentence };
            }
        }
    }

    // Pattern B: table format "| 中文 | **term** | meaning |"
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line.startsWith('|')) continue;
        if (line.match(/^\|[-:\s|]+\|/)) continue;
        const cells = line.split('|').map(c => c.trim()).filter(c => c);
        if (cells.length < 2) continue;
        let termText = '';
        let meaning = '';
        for (const cell of cells) {
            const inner = cell.replace(/^\*\*|\*\*$/g, '').replace(/<br\s*\/?>/gi, ' ').trim();
            if (cell.includes('**') && !/[\u4e00-\u9fff]/.test(inner)) {
                termText = inner.trim();
            } else if (/[\u4e00-\u9fff]/.test(inner) && inner.length > 2) {
                meaning += (meaning ? ' ' : '') + inner;
            }
        }
        if (termText && meaning && termText.length < 80 && !details[termText]) {
            details[termText] = { meaning, sentence: '' };
            const shortKey = termText.split('/')[0].trim().split(' /')[0].trim();
            if (shortKey && shortKey !== termText && !details[shortKey]) {
                details[shortKey] = { meaning: '', sentence: '' };
            }
        }
    }

    return details;
}

// ─── 为文本注入 interactive-term span ───────────────────────
// 保护 <code> 和 <pre> 内部：不做词汇高亮，避免 markdown-it 转义嵌套
function wrapTerms(text, termDetails) {
    if (!text || !termDetails) return text;
    const protectedBlocks = [];

    // 保护 code/pre 块
    let result = text.replace(/<code>[\s\S]*?<\/code>|<pre>[\s\S]*?<\/pre>/g, (match) => {
        protectedBlocks.push(match);
        return `\u0000CODE${protectedBlocks.length - 1}\u0000`;
    });

    const sortedTerms = Object.keys(termDetails).sort((a, b) => b.length - a.length);
    for (const term of sortedTerms) {
        // 保护已生成的 interactive-term 块（含其 data-* 属性值），
        // 防止后续较短词汇在其内部（尤其 data-sentence 例句中）二次包裹
        result = result.replace(/<span class="interactive-term"[\s\S]*?<\/span>/g, (match) => {
            protectedBlocks.push(match);
            return `\u0000CODE${protectedBlocks.length - 1}\u0000`;
        });

        const detail = termDetails[term];
        const safe = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const re = new RegExp('(?<!\\w)' + safe + '(?!\\w)', 'gi');
        result = result.replace(re, (match) => {
            totalTerms++;
            const m = escapeHtml(detail.meaning || '');
            const s = escapeHtml(detail.sentence || '');
            return `<span class="interactive-term" data-term="${escapeHtml(match)}" data-meaning="${m}" data-sentence="${s}">${match}</span>`;
        });
    }

    // 还原所有保护块
    result = result.replace(/\u0000CODE(\d+)\u0000/g, (_, idx) => protectedBlocks[parseInt(idx)]);
    return result;
}
// ─── 渲染知识卡片（Cheat Sheet） ─────────────────────────────
function renderCheatCards(rawLines, termDetails) {
    const lines = rawLines.filter(l => l.trim() !== '' && l.trim() !== '---');
    if (lines.length === 0) return null;
    const cards = [];

    // Check if any line is a table data row
    const isTableFormat = lines.some(l => l.trim().startsWith('|') && !l.trim().match(/^\|[-:\s|]+\|/) && l.includes('**'));

    if (isTableFormat) {
        for (const line of lines) {
            const t = line.trim();
            if (!t.startsWith('|') || t.match(/^\|[-:\s|]+\|/)) continue;
            const cells = t.split('|').map(c => c.trim()).filter(c => c);
            let termText = '';
            let meaning = '';
            let sentence = '';
            for (const cell of cells) {
                // 清理 <br> 和多余 HTML
                const inner = cell.replace(/^\*\*|\*\*$/g, '').replace(/<br\s*\/?>/gi, ' ').trim();
                if (cell.includes('**') && !/[\u4e00-\u9fff]/.test(inner)) {
                    termText = inner.trim();
                } else if (/[\u4e00-\u9fff]/.test(inner) && inner.length > 2 && !meaning) {
                    meaning = inner;
                } else if (inner && !meaning) {
                    meaning = inner;
                } else if (inner) {
                    sentence += (sentence ? ' ' : '') + inner;
                }
            }
            if (termText && meaning && termText.length < 80) {
                cards.push({ term: termText, meaning, sentence });
                termDetails[termText] = { meaning, sentence };
                const sk = termText.split('/')[0].trim().split(' /')[0].trim();
                if (sk && sk !== termText && !termDetails[sk]) termDetails[sk] = { meaning, sentence };
            }
        }
    } else {
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            const numMatch = line.match(/^(\d+)\.\s*\*\*(.+?)\*\*/);
            if (!numMatch) continue;
            const termRaw = numMatch[2].trim();
            if (termRaw.length > 80) continue;
            let meaning = '';
            let sentence = '';
            let j = i + 1;
            while (j < lines.length) {
                const l = lines[j].trim();
                if (l === '' || l.startsWith('---') || /^#{1,3}\s/.test(l) || /^\d+\.\s+\*\*/.test(l)) break;
                const mm = l.match(/^\*\*中文解释\*\*[：:]\s*(.+)$/);
                const sm = l.match(/^\*\*商业造句\*\*[：:]\s*(.+)$/);
                if (mm) meaning += (meaning ? ' ' : '') + mm[1].trim();
                if (sm) sentence += (sentence ? ' ' : '') + sm[1].trim();
                j++;
            }
            if (!meaning) {
                const after = line.replace(/^(\d+)\.\s*\*\*[^*]+\*\*/, '').trim();
                if (after && /[\u4e00-\u9fff]/.test(after)) meaning = after.replace(/^—+/, '').trim();
            }
            if (meaning && termRaw.length < 80) {
                cards.push({ term: termRaw, meaning, sentence });
                termDetails[termRaw] = { meaning, sentence };
                const sk = termRaw.split('/')[0].trim().split(' /')[0].trim();
                if (sk && sk !== termRaw && !termDetails[sk]) termDetails[sk] = { meaning, sentence };
            }
        }
    }
    if (cards.length === 0) return null;

    const cardEls = cards.map(c => {
        const t = escapeHtml(c.term);
        const m = escapeHtml(c.meaning);
        const s = escapeHtml(c.sentence);
        return `<div class="cheat-item" data-term="${t}" data-meaning="${m}" data-sentence="${s}">` +
               `<span class="cheat-item__term">${t}</span>` +
               `<span class="cheat-item__sep">—</span>` +
               `<span class="cheat-item__meaning">${m}</span>` +
               `</div>`;
    }).join('\n');

    // 词条紧凑两栏/单行网格（词 + 释义同行，斜体印刷体 + 楷体备注感，不抢戏）
    return `<div class="cheat-note-grid">\n${cardEls}\n</div>`;
}

// ─── 将文本拆分为独立段落列表 ───────────────────────────────
// Returns { cnParas: string[], enParas: string[] }
function splitParagraphs(rawLines) {
    const cnParas = [];
    const enParas = [];
    let buf = '';
    let lang = null; // 'cn' or 'en'
    let i = 0;

    // Chinese sentence-ending punctuation
    const cnEndPunct = /[。！？，；：""''）】》、]/;
    // English sentence-ending punctuation
    const enEndPunct = /[.!?]/;

    function lastBufLine() {
        return buf.trim().split('\n').pop() || '';
    }

    function shouldMerge(lastLine, nextLine) {
        if (!lastLine || !nextLine) return false;
        const lastIsCN = /[\u4e00-\u9fff]/.test(lastLine.trim());
        const nextIsCN = /[\u4e00-\u9fff]/.test(nextLine.trim());
        if (lastIsCN !== nextIsCN) return false;
        if (lastIsCN) {
            return !cnEndPunct.test(lastLine.trim()[lastLine.trim().length - 1]);
        } else {
            return !enEndPunct.test(lastLine.trim()[lastLine.trim().length - 1]);
        }
    }

    function flush() {
        if (!buf) return;
        const trimmed = buf.trim();
        if (!trimmed) { buf = ''; return; }
        if (lang === 'cn') cnParas.push(trimmed);
        else if (lang === 'en') enParas.push(trimmed);
        buf = '';
    }

    while (i < rawLines.length) {
        const t = rawLines[i].trim();

        if (t === '' || t === '---') {
            // Lookahead: skip empty line if next content should merge with buf
            let j = i + 1;
            while (j < rawLines.length && rawLines[j].trim() === '') j++;
            const nextContent = rawLines[j] ? rawLines[j].trim() : '';
            if (buf && nextContent && shouldMerge(lastBufLine(), nextContent)) {
                // Peek at next content instead of flushing now
                // Skip this empty line and continue collecting
                i++;
                continue;
            }
            flush();
            i++;
            continue;
        }

        const isCN = isChineseLine(t);
        const isEN = isEnglishLine(t);
        if (isCN) {
            if (lang === 'en') flush();
            lang = 'cn';
            if (buf) {
                if (shouldMerge(lastBufLine(), t)) {
                    buf += t;
                } else {
                    buf += '\n' + t;
                }
            } else {
                buf = t;
            }
        } else if (isEN) {
            if (lang === 'cn') flush();
            lang = 'en';
            if (buf) {
                if (shouldMerge(lastBufLine(), t)) {
                    buf += ' ' + t;
                } else {
                    buf += '\n' + t;
                }
            } else {
                buf = t;
            }
        } else {
            if (/[\u4e00-\u9fff]/.test(t)) {
                if (lang === 'en') flush();
                lang = 'cn';
                if (buf) {
                    if (shouldMerge(lastBufLine(), t)) {
                        buf += t;
                    } else {
                        buf += '\n' + t;
                    }
                } else {
                    buf = t;
                }
            } else {
                if (lang === 'cn') flush();
                lang = 'en';
                if (buf) {
                    if (shouldMerge(lastBufLine(), t)) {
                        buf += ' ' + t;
                    } else {
                        buf += '\n' + t;
                    }
                } else {
                    buf = t;
                }
            }
        }
        i++;
    }
    flush();
    return { cnParas, enParas };
}
function renderBilingualPair(cnText, enText, termDetails, isFirstEn) {
    const paras = [];
    if (cnText && cnText.trim()) {
        paras.push(`<p class="cn-para">${wrapTerms(escapeHtml(cnText.trim()), termDetails)}</p>`);
    }
    if (enText && enText.trim()) {
        // ReadShift 翻译：包裹在陶土橙左边线框架内，明确标记为二创翻译
        paras.push(`<div class="rebook-translation">`
            + `<span class="rebook-translation__label">ReadShift 双语翻译</span>`
            + `<p class="en-para${isFirstEn ? ' en-first' : ''}">${wrapTerms(escapeHtml(enText.trim()), termDetails)}</p>`
            + `</div>`);
    }
    if (paras.length === 0) return null;
    return `<div class="bilingual-pair">\n${paras.join('\n')}\n</div>`;
}

// ─── 处理单个文件 ────────────────────────────────────────────
function processFile(filePath, pageNum) {
    let content = fs.readFileSync(filePath, 'utf8');
    content = content.replace(/小編微信號[^\n]+/g, '')
                     .replace(/【幸福的味道】[^\n]+/g, '')
                     .replace(/關注[^\n]+/g, '')
                     .replace(/周讀[^\n]+/g, '')
                     .replace(/ireadweek[^\n]+/g, '')
                     .replace(/<!-- PROCESSED -->/g, '');

    const termDetails = extractTermDetails(content);
    const lines = content.split('\n');
    const output = [];
    let i = 0;
    let globalENIndex = 0;

    while (i < lines.length) {
        const trimmed = lines[i].trim();

        // Skip empty / separator
        if (trimmed === '' || trimmed === '---') { i++; continue; }

        // ── HTML 直通块（目录、序言卡片等以 < 开头的结构直接原样注入） ──
        if (trimmed.startsWith('<')) {
            const htmlLines = [];
            // 收集完整 HTML 块（直到遇到非HTML空行分隔）
            while (i < lines.length) {
                const l = lines[i].trim();
                if (l === '' || l === '---') break;
                htmlLines.push(lines[i]);
                i++;
            }
            const rawHtml = htmlLines.join('\n');
            // 直接原样注入，不做任何转义或语言拆分；
            // 但 rebook-translation 块内的 en-para 内容仍要做术语高亮（wrapTerms）
            let processed = rawHtml;
            if (rawHtml.includes('rebook-translation') && rawHtml.includes('en-para')) {
                processed = rawHtml.replace(/<p class="en-para[^"]*">([\s\S]*?)<\/p>/g, (m, inner) => {
                    return m.replace(inner, wrapTerms(inner, termDetails));
                });
            }
            output.push(processed);
            continue;
        }

        // ── 特殊区块（最高优先级，先于普通标题检测） ──
        if (isCheatSheetHeader(trimmed)) {
            const sectionLines = [trimmed];
            i++;
            while (i < lines.length) {
                const l = lines[i].trim();
                if (l === '---' || /^#{1,3}\s/.test(l) || l.startsWith('<')) break;
                sectionLines.push(lines[i]);
                i++;
            }
            const cardsHtml = renderCheatCards(sectionLines, termDetails);
            if (cardsHtml) {
                // 紧凑注脚样式：一行标题 + 紧凑词条，短小精悍不抢戏
                output.push(`<div class="rebook-card">` +
                    `<div class="rebook-card__title">Cheat Sheet · 商业语汇</div>` +
                    `<div class="rebook-card__body">${cardsHtml}</div></div>`);
            }
            continue;
        }
        if (isRhetoricHeader(trimmed)) {
            const blockLines = [trimmed];
            i++;
            while (i < lines.length) {
                const l = lines[i].trim();
                // 注意：rhetoric-note 等 HTML span 是赏析内容的一部分，必须继续收集（不能按 < 开头 break）
                if (l === '---' || l.startsWith('<div id="sec-') || l.startsWith('<div class="preface-card"') || l.startsWith('<div class="rebook-translation"') || (/^#{1,3}\s/.test(l) && !isRhetoricHeader(l))) break;
                blockLines.push(lines[i]);
                i++;
            }
            // 语言赏析紧凑注脚（剔除源文件的标题行，避免与卡片标题重复）
            const label = trimmed.replace(/^#+\s*/, '').replace(/^\d+\.\s*/, '').trim();
            const bodyLines = blockLines.filter((l, idx) => idx !== 0);
            // 语言赏析紧凑注脚：完整提取 rhetoric-note 结构（zh+en 一体），占位符保护后渲染还原，绝对抛弃块内任何裸露重复段落！
            // ⚠️ 必须匹配到 rhetoric-note 的完整闭合（</span></span>），非贪婪到第一个 </span> 会截断丢弃 en！
            const noteHolders = [];
            let bodyText = bodyLines.join('\n');
            bodyText = bodyText.replace(/<span class="rhetoric-note">[\s\S]*?<\/span>\s*<\/span>/g, (m) => {
                noteHolders.push(m);
                return `\n@@RNOTE${noteHolders.length - 1}@@\n`;
            });
            let cardBodyHtml = '';
            if (noteHolders.length > 0) {
                const rendered = md.render(bodyText);
                cardBodyHtml = rendered.replace(/@@RNOTE(\d+)@@/g, (_, i) => noteHolders[parseInt(i)]);
            } else {
                cardBodyHtml = md.render(bodyText);
            }
            output.push(`<div class="rebook-card">` +
                `<div class="rebook-card__title">${escapeHtml(label)}<span class="rebook-card__title-en"> · Language &amp; Logic Appreciation</span></div>` +
                `<div class="rebook-card__body">${cardBodyHtml}</div></div>`);
            continue;
        }
        if (isKnowledgeHeader(trimmed)) {
            const blockLines = [trimmed];
            i++;
            while (i < lines.length) {
                const l = lines[i].trim();
                if (l === '---' || l.startsWith('<div id="sec-') || l.startsWith('<div class="preface-card"') || l.startsWith('<div class="rebook-translation"') || (/^#{1,3}\s/.test(l) && !isKnowledgeHeader(l))) break;
                blockLines.push(lines[i]);
                i++;
            }
            // 外链知识窗紧凑注脚（剔除源文件的标题行，避免与卡片标题重复）
            const label = trimmed.replace(/^#+\s*/, '').replace(/^\d+\.\s*/, '').trim();
            const bodyLines = blockLines.filter((l, idx) => idx !== 0);
            output.push(`<div class="rebook-card">` +
                `<div class="rebook-card__title">${escapeHtml(label)}<span class="rebook-card__title-en"> · Beyond the Text</span></div>` +
                `<div class="rebook-card__body">${md.render(bodyLines.join('\n'))}</div></div>`);
            continue;
        }

        // ── 小节标题（## 级）：登记两级目录并渲染为居中加粗子标题 ──
        // 形如："## 年轻有活力的公司" 或 "## 37岁时我已任德州仪器公司副总裁"
        // 该分支必须放在「普通标题」之前，否则 ## 会落入 md.render 只输出 <h2>、
        // 既不生成 sub-* 锚点也不登记 subsections，导致目录下拉缺小节条目。
        const mdSubMatch = trimmed.match(/^##\s+(.+)$/);
        if (mdSubMatch) {
            const title = mdSubMatch[1].trim();
            if (title) {
                // 英文副标题：紧接 ## 后一行若为纯英文短语（非 HTML/标题/列表/表格），则作为 en 渲染
                let en = '';
                if (i + 1 < lines.length) {
                    const nxt = lines[i + 1].trim();
                    if (nxt && /^[A-Za-z]/.test(nxt) && !nxt.startsWith('<') && !nxt.startsWith('#') && !nxt.startsWith('|') && !nxt.startsWith('-')) {
                        en = nxt;
                        i++; // 消费英文副标题行
                    }
                }
                const subId = `sub-${pageNum}-${subsectionSeq++}`;
                subsections.push({
                    id: subId,
                    zh: title,
                    en,
                    chapterStart: currentChapterStart,
                    page: pageNum
                });
                output.push(`<h3 class="subsection-title" id="${subId}"><span class="subsection-title__zh">${escapeHtml(title)}</span>` +
                    (en ? `<span class="subsection-title__en">${escapeHtml(en)}</span>` : '') + `</h3>`);
                i++;
                continue;
            }
        }

        // ── 普通标题 ──
        if (/^#{1,3}\s/.test(trimmed)) {
            const headerLines = [trimmed];
            i++;
            while (i < lines.length && lines[i].trim() !== '' && !lines[i].trim().startsWith('#')) {
                headerLines.push(lines[i]);
                i++;
            }
            output.push(md.render(wrapTerms(headerLines.join('\n'), termDetails)));
            continue;
        }

        // ── 小节标题（原书子板块）：孤立短中文行 + 紧跟翻译块 → 居中加粗子标题 ──
        // 形如："人生重要分界\n\n<div class=rebook-translation>...A Pivotal Watershed...</div>"
        // 排除：① 句末有标点（。！？）的句子——多是正文短句/过渡句，不是标题；
        //       ② 标题后面若紧跟下一标题（无正文），属假标题，交由正文处理
        const subsectionMatch = trimmed.match(/^([^<#]{2,14})$/);
        const subsectionNoEndPunct = subsectionMatch && !/[。！？!?]$/.test(trimmed.trim());
        if (subsectionMatch && subsectionNoEndPunct && /[\u4e00-\u9fff]/.test(trimmed)) {
            const title = trimmed.trim();
            // 预读下一行（跳过空行）是否紧跟翻译块
            let look = i + 1;
            while (look < lines.length && lines[look].trim() === '') look++;
            const nextTrim = look < lines.length ? lines[look].trim() : '';
            if (nextTrim.startsWith('<div class="rebook-translation"')) {
                // 收集该标题对应的翻译块（仅紧跟的一个）
                const transLines = [];
                let j = i + 1;
                while (j < lines.length && lines[j].trim() === '') j++;
                while (j < lines.length) {
                    const l = lines[j].trim();
                    if (l === '' || l === '---') break;
                    transLines.push(lines[j]);
                    j++;
                }
                const transHtml = transLines.join('\n');
                const enMatch = transHtml.match(/<p class="en-para">(.*?)<\/p>/s);
                const enText = enMatch ? enMatch[1] : '';
                // 检查翻译是否就是该标题的翻译（英文较短 ≤ 120 字符，且无句号结尾=标题式短语）
                const enPlain = enText ? enText.replace(/<[^>]+>/g, '').trim() : '';
                const enIsPhrase = enPlain.length <= 120 && !/\.$/.test(enPlain) && enPlain.length > 0;
                if (enIsPhrase) {
                    const subId = `sub-${pageNum}-${subsectionSeq++}`;
                    // 收集到目录结构（全局小节列表）
                    subsections.push({
                        id: subId,
                        zh: title,
                        en: enPlain,
                        chapterStart: currentChapterStart,
                        page: pageNum
                    });
                    output.push(`<h3 class="subsection-title" id="${subId}"><span class="subsection-title__zh">${escapeHtml(title)}</span>` +
                        (enPlain ? `<span class="subsection-title__en">${enPlain}</span>` : '') + `</h3>`);
                    i = j; // 跳过已消费的翻译块行
                    continue;
                }
            }
        }

        // ── 双语段落块：收集直到 ---、标题、HTML 块 或 EOF，然后拆分配对 ──
        const blockLines = [];
        while (i < lines.length) {
            const l = lines[i].trim();
            if (l === '---') { i++; break; }
            if (/^#{1,3}\s/.test(l) || isCheatSheetHeader(l) || isRhetoricHeader(l) || isKnowledgeHeader(l)) break;
            // 遇到 HTML 直通块（以 < 开头）立即断开，交回主循环处理
            if (l.startsWith('<')) break;
            blockLines.push(lines[i]);
            i++;
        }

        const { cnParas, enParas } = splitParagraphs(blockLines);
        const maxLen = Math.max(cnParas.length, enParas.length);
        for (let p = 0; p < maxLen; p++) {
            const cn = p < cnParas.length ? cnParas[p] : '';
            const en = p < enParas.length ? enParas[p] : '';
            const isFirst = (globalENIndex === 0 && enParas.length > 0 && p === 0);
            const pairHtml = renderBilingualPair(cn, en, termDetails, isFirst);
            if (pairHtml) output.push(pairHtml);
            if (en) globalENIndex++;
        }
    }

    return output.join('\n');
}

// ─── 主流程 ─────────────────────────────────────────────────
const allHtmlParts = [];
let lastChapterStart = -1;
for (const file of files) {
    // files 可能是绝对路径（多章合成）或纯文件名（单章），统一取绝对路径
    const filePath = path.isAbsolute(file) ? file : path.join(fullDir, file);
    // 从文件名提取页码
    const pageMatch = path.basename(file).match(/page_(\d+)/);
    const pageNum = pageMatch ? parseInt(pageMatch[1]) : 0;

    // 页码过滤
    if (pageFilter && pageNum > 0 && !pageFilter(pageNum)) continue;

    // 记录当前章节起始页（小节归属用）
    if (pageNum > 0) {
        const ch = getChapterForPage(pageNum);
        currentChapterStart = ch ? ch.start : currentChapterStart;
    }

    // 判断是否为章节起始页（页码落在章节映射的 start 上，且不是目录/引导页）
    let isSectionStart = false;
    if (pageNum > 0) {
        for (const ch of CHAPTER_MAP) {
            if (pageNum === ch.start && pageNum > 3) { // 跳过目录(3)本身
                isSectionStart = true;
                break;
            }
        }
    }

    const fileContent = processFile(filePath, pageNum);
    if (pageNum > 0 && fileContent) {
        // 加入章节导航条（仅章节起始页渲染，正文中不重复出现）
        const nav = renderChapterNav(pageNum, isSectionStart);
        if (lastChapterStart !== pageNum) {
            allHtmlParts.push(nav + '\n' + fileContent);
            lastChapterStart = pageNum;
        } else {
            allHtmlParts.push(fileContent);
        }
    } else {
        allHtmlParts.push(fileContent);
    }
}

let bodyContent = allHtmlParts.join('\n\n');

// ── 裁剪「全书目录卡」(toc-card) 中指向本次未渲染章节的章链接 ──
// 第一章 source 里自带一张全书目录卡，列出全部六章；无论是单章(--chapter 1)
// 还是多章合成，凡 toc-card 里指向"本次未包含"章的 chap-# 链接都会成断头锚点，
// 这里统一裁掉(仅在渲染时处理,不动 source 本身)。序言用 sec-* 前缀、不匹配 chap- 正则，天然保留。
{
    const scopeStarts = new Set();
    if (multiChapter) {
        const chNums = chaptersArg.split(',').map(s => s.trim()).filter(Boolean);
        for (const cn of chNums) scopeStarts.add(chapterStartOf(parseInt(cn)));
    } else if (chapterArg) {
        // 单章：范围只含本章起始页；第一章=23,其余按章号映射
        scopeStarts.add(chapterStartOf(parseInt(chapterArg) || 1));
    }
    if (scopeStarts.size) {
        bodyContent = bodyContent.replace(
            /(<li class="toc-card__item">\s*<a href="#)(chap-\d+)("[\s\S]*?<\/li>)/g,
            (m, pre, href) => {
                const pageNum = parseInt((href.match(/\d+/) || ['0'])[0], 10);
                return scopeStarts.has(pageNum) ? m : '';
            }
        );
    }
}
function chapterStartOf(n) {
    return n === 1 ? 23 : n === 2 ? 46 : n === 3 ? 64 : n === 4 ? 78 : n === 5 ? 93 : 101;
}

// 修复 markdown-it 可能转义的 class 属性
bodyContent = bodyContent
    .replace(/&lt;span class=['"]interactive-term['"]/g, '<span class="interactive-term">')
    .replace(/&lt;span class=['"]cheat-card['"]/g, '<span class="cheat-card">');

// ── 完全本地化：将 Alpine.js 内联进 HTML（零外部依赖，离线可用） ──
const alpineSrc = fs.readFileSync(path.join(__dirname, '..', 'src', 'assets', 'alpine.min.js'), 'utf8');

// ═══ 构建两级目录数据（章 → 小节） ═══
const tocData = subsections.map(s => ({
    id: s.id,
    zh: s.zh,
    en: s.en,
    chapterStart: s.chapterStart,
    page: s.page,
}));
const tocJson = JSON.stringify(tocData);

// ═══ 章列表（导航面板顶层跳转用） ═══
// 从 CHAPTER_MAP + 已收集的小节，得到实际渲染的章（含序言分组标记）
const frontStarts = new Set([7, 12, 14]); // 序一/序二/自序的起始页（并入第一章卷首）
function buildChapterList() {
    let chapters = [];
    if (multiChapter) {
        const chNums = chaptersArg.split(',').map(s => s.trim()).filter(Boolean);
        for (const cn of chNums) {
            const startPage = parseInt(cn) === 1 ? 23 :
                              parseInt(cn) === 2 ? 46 :
                              parseInt(cn) === 3 ? 64 :
                              parseInt(cn) === 4 ? 78 :
                              parseInt(cn) === 5 ? 93 : 101;
            const ch = CHAPTER_MAP.find(c => c.start === startPage);
            if (ch) chapters.push({
                start: ch.start,
                anchor: `chap-${ch.start}`,
                zh: ch.title_zh || ch.name,
                en: ch.title_en || '',
                hasPreface: parseInt(cn) === 1,
            });
        }
    } else {
        // 单章模式：仍输出当前章一项（保持 template 兼容）
        const startPage = { '1': 23, '2': 46, '3': 64, '4': 78, '5': 93, '6': 101 }[chapterArg] || 23;
        const ch = CHAPTER_MAP.find(c => c.start === startPage);
        if (ch) chapters.push({
            start: ch.start,
            anchor: `chap-${ch.start}`,
            zh: ch.title_zh || ch.name,
            en: ch.title_en || '',
            hasPreface: chapterArg === '1' || chapterArg === '',
        });
    }
    return chapters;
}
const chapterList = buildChapterList();
const chapterListJson = JSON.stringify(chapterList);

// ═══ 章节大标题（导航面板用，单章模式）：按 chapterArg 从 CHAPTER_MAP 取 ═══
function resolveChapterLabels() {
    const target = chapterArg ? parseInt(chapterArg, 10) : 1;
    const labels = { '1': ['第一章 大时代中的幼少年', 'Childhood & Youth in a Great Era'],
                     '2': ['第二章 哈佛大学与麻省理工', 'Harvard and MIT'],
                     '3': ['第三章 进入半导体业', 'Entering the Semiconductor Industry'],
                     '4': ['第四章 初试啼声', 'First Signs of Promise'],
                     '5': ['第五章 重拎书包', 'Back to School'],
                     '6': ['附录 张忠谋大事年表', 'A Chronology of Morris Chang'] };
    const hit = labels[String(target)];
    if (hit) return { chapter_label_zh: hit[0], chapter_label_en: hit[1] };
    const ch = CHAPTER_MAP.find(c => c.start === target) || getChapterForPage(target);
    return {
        chapter_label_zh: (ch && ch.title_zh) || (ch && ch.name) || '第一章 大时代中的幼少年',
        chapter_label_en: (ch && ch.title_en) || 'Childhood & Youth in a Great Era',
    };
}
const chapterLabels = resolveChapterLabels();

const finalHtml = ejs.render(template, {
    title: '张忠谋自传 · 双语典藏版',
    body_content: bodyContent,
    term_count: totalTerms,
    current_mode: 'Gemini 3.6 Flash + Agnes 2.5 Flash',
    alpine_inline: `<script defer>${alpineSrc}</script>`,
    toc_json: tocJson,
    chapter_list_json: chapterListJson,
    multi_chapter: multiChapter,
    chapter_num: chapterArg || "1",
    chapter_label_zh: chapterLabels.chapter_label_zh,
    chapter_label_en: chapterLabels.chapter_label_en,
});

fs.writeFileSync(outPath, finalHtml, 'utf8');
console.log('\n✅ 已生成 v9 杂志级排版: ' + outPath
    + ' (' + files.length + ' pages, ' + totalTerms + ' terms, ' + (finalHtml.length / 1024).toFixed(0) + ' KB)');
