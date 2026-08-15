/**
 * ReadShift HTML 渲染器 v8 — 出版级双语排版
 *
 * 核心规则：
 *   1. 每页以  开头
 *   2. 正文用 <p class="cn-para"> / <p class="en-para"> 双段，无 <h2> 包裹段落
 *   3. 知识卡片用 .knowledge-card div，不用 markdown list
 *   4. 彻底清除广告水印与中间处理杂讯
 */

const ejs = require('ejs');
const MarkdownIt = require('markdown-it');
const fs = require('fs');
const path = require('path');

const md = new MarkdownIt({ html: true, linkify: true, typographer: true });
const templatePath = path.join(__dirname, '..', 'src', 'templates', 'template.ejs');
const template = fs.readFileSync(templatePath, 'utf8');

const fullDir = path.join(__dirname, '..', 'output', 'full');
const files = fs.readdirSync(fullDir).filter(f => f.endsWith('.md') && f !== '_INDEX.md').sort();

let totalTerms = 0;

// ── helpers ──────────────────────────────────────────────────────────────────
const hasChinese = s => /[\u4e00-\u9fff]/.test(s);
const hasEnglish = s => /[a-zA-Z]{3,}/.test(s);

// Ad / watermark patterns
const adRepls = [
    [/小編微信號[^\n]*/g, ''],
    [/【幸福的味道】[^\n]*/g, ''],
    [/关注[^\n]*/g, ''],
    [/關注[^\n]*/g, ''],
    [/周讀[^\n]*/g, ''],
    [/ireadweek[^\n]*/g, ''],
    [/微信[^\n]*/g, ''],
];

function stripAds(content) {
    for (const [re, rep] of adRepls) content = content.replace(re, rep);
    return content;
}

// Strip noise lines from within a segment
function cleanSegment(seg) {
    // Remove inline ## N. headers (keep content after them)
    seg = seg.replace(/\n##\s+(1\.|2\.|3\.)\s*[^\n]*/g, '\n');
    // Remove standalone header-only lines at segment start
    let lines = seg.split('\n');
    // Strip leading ## headers from each segment
    lines = lines.filter(l => {
        const t = l.trim();
        if (/^##\s+(1\.|2\.|3\.)\s/.test(t)) return false;
        if (/^##\s+双语重塑$/.test(t)) return false;
        if (/^##\s+修复文本$/.test(t)) return false;
        if (/^##\s+知识萃取$/.test(t)) return false;
        if (/^##\s+双语对照版$/.test(t)) return false;
        if (/^·\s*ReadShift\s*全量生产$/.test(t)) return false;
        if (/^#\s*《张忠谋自传》/.test(t)) return false;
        if (/^#\s*\d+页$/.test(t)) return false;
        if (/^#\s*(双语传记片段|为历史留下纪录|Preserving\s*History|附|自序|写传的)$/.test(t)) return false;
        if (/^###\s*(📌|🎯|🌐|商业语汇提炼|修辞与逻辑赏析|外链知识窗|知识卡片)/.test(t)) return false;
        return true;
    });
    let result = lines.join('\n')
        .replace(/以下是基于输入中英对照正文重新萃取的成果[：:]\s*/g, '')
        .replace(/<!--\s*PROCESSED\s*-->/g, '')
        .trim();
    return result;
}

// ── term extraction ───────────────────────────────────────────────────────────
function extractTerms(content) {
    const seen = new Set();
    const terms = [];
    const lines = content.split('\n');
    const meanings = {};   // term → meaning
    const sentences = {};  // term → 商业造句 context

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Pattern A: **term**  /  **N. term**
        const m1 = line.match(/^\*\*(?:\d+\.\s*)?([^*]+?)\*\*$/);
        if (m1 && i + 1 < lines.length) {
            const key = m1[1].trim().replace(/^\d+\.\s*/, '');
            if (key && key.length > 1 && !key.includes('：') && !key.includes(':')) {
                const next = lines[i + 1].trim();
                const mx = next.match(/^\*\*中文解释\*\*[：:]\s*(.+)$/);
                if (mx) meanings[key] = mx[1].trim();
            }
        }

        // Pattern B: N. **term**
        const m2 = line.match(/^\d+\.?\s*\*\*([^*]+?)\*\*/);
        if (m2 && i + 1 < lines.length) {
            const key = m2[1].trim();
            if (key && key.length > 1 && !key.includes('：') && !key.includes(':')) {
                const next = lines[i + 1].trim();
                const mx = next.match(/^\*\*中文解释\*\*[：:]\s*(.+)$/);
                if (mx) meanings[key] = mx[1].trim();
            }
        }

        // Pattern C: table row | **term** |
        const m3 = line.match(/^\|\s*\*\*([^*]+?)\*\*\s*\|/);
        if (m3 && i + 1 < lines.length && lines[i + 1].trim().match(/^\|[-:\s|]+\|/)) {
            let j = i + 2;
            while (j < lines.length && lines[j].trim().match(/^\|[-:\s|]+\|/)) j++;
            if (j < lines.length) {
                const mx = lines[j].trim().match(/^\|[^|]*\*\*([^*]+?)\*\*/);
                if (mx) meanings[m3[1].trim()] = mx[1].trim();
            }
        }

        // Pattern D: **term** followed by **商业造句**: sentence
        const m4 = line.match(/^\*\*([^*]+?)\*\*$/);
        if (m4 && i + 1 < lines.length) {
            const key = m4[1].trim();
            if (key && key.length > 2 && !key.includes('：') && !key.includes(':')) {
                const nx = lines[i + 1].trim();
                const sx = nx.match(/^\*\*商业造句\*\*[：:]\s*(.+)$/);
                if (sx) sentences[key] = sx[1].trim();
            }
        }
    }

    for (const raw of Object.keys(meanings)) {
        if (seen.has(raw)) continue;
        seen.add(raw);
        const meaning = meanings[raw] || sentences[raw] || '';
        if (meaning && raw.length > 1) terms.push({ term: raw, meaning });
    }
    return terms;
}

function wrapTerms(html, terms) {
    let result = html;
    for (const t of terms) {
        const esc = t.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        try {
            const re = new RegExp('(' + esc + ')', 'g');
            if (result.match(re)) {
                result = result.replace(re, (m) => {
                    totalTerms++;
                    return `<span class="interactive-term" data-term="${t.term.replace(/"/g, '&quot;')}" data-meaning="${t.meaning.replace(/"/g, '&quot;')}">${m}</span>`;
                });
            }
        } catch (_) { /* skip */ }
    }
    return result;
}

// ── knowledge card extraction ────────────────────────────────────────────────
function extractKnowledgeCards(content) {
    const lines = content.split('\n');
    const buffers = { cheat: [], rhetoric: [], link: [] };
    let buf = null;

    for (const line of lines) {
        if (/^###\s*📌\s*Cheat\s*Sheet/.test(line) || /^###\s*商业语汇提炼/.test(line)) { buf = 'cheat'; continue; }
        if (/^###\s*🎯\s*修辞/.test(line) || /^###\s*修辞与逻辑赏析/.test(line)) { buf = 'rhetoric'; continue; }
        if (/^###\s*🌐\s*外链/.test(line) || /^###\s*外链知识窗/.test(line))  { buf = 'link';   continue; }
        if (/^###\s*知识卡片/.test(line))                                      { buf = null; continue; }
        if (buf && !line.startsWith('---') && !line.startsWith('<!--') && line.trim()) {
            buffers[buf].push(line);
        }
    }

    const labels = { cheat: '📌 Cheat Sheet · 地道商业表达', rhetoric: '🎯 修辞与逻辑赏析', link: '🌐 外链知识窗' };
    const has = { cheat: buffers.cheat.join('\n').length > 30, rhetoric: buffers.rhetoric.join('\n').length > 30, link: buffers.link.join('\n').length > 30 };

    if (!has.cheat && !has.rhetoric && !has.link) return '';

    let html = '<div class="knowledge-cards">\n';
    for (const key of ['cheat', 'rhetoric', 'link']) {
        if (!has[key]) continue;
        // Strip any remaining header lines from buffer so md.render doesn't create h2s
        const cleanBody = buffers[key].filter(l => !/^#{1,3}\s/.test(l.trim())).join('\n');
        html += `  <div class="knowledge-card ${key}">\n`;
        html += `    <div class="card-label">${labels[key]}</div>\n`;
        html += `    <div class="card-body">${md.render(cleanBody)}</div>\n`;
        html += `  </div>\n`;
    }
    html += '</div>\n';
    return html;
}

// ── process one file ─────────────────────────────────────────────────────────
function processFile(filename, rawContent) {
    const content = stripAds(rawContent);
    const pageNum = filename.match(/page_(\d+)/)?.[1] ?? '??';
    const terms = extractTerms(content);

    // ── Line-level processing (works regardless of --- separators) ──────────
    // Key insight: split at # headers into sections, then process each section independently.
    // This prevents pure-CN intro text from being merged with bilingual content in a later section.
    const allLines = content.split('\n');
    const sections = []; // [[lines]]
    let currentSection = [];

    for (const rawLine of allLines) {
        const line = rawLine.trim();
        // Flush section at major header boundaries (#  or ## )
        if (/^#{1,2}\s/.test(line) && line.length < 80) {
            if (currentSection.length > 0) {
                sections.push(currentSection);
                currentSection = [];
            }
        }
        currentSection.push(line);
    }
    if (currentSection.length > 0) sections.push(currentSection);

    const blocks = []; // [{type:'cn'|'en'|'title', lines:[]}]
    const pairSections = []; // sections that have both CN and EN content
    const cnOnlySections = []; // sections that are purely CN

    for (const section of sections) {
        const sectionBlocks = [];
        let curBlock = null;

        for (const rawLine of section) {
            const line = rawLine.trim();

        // Skip noise lines
        if (!line || line === '---' || line === '...' || line.startsWith('<!--')) continue;
        // Skip all ## and ### header lines (these are structural, not content)
        if (/^#{2,3}\s/.test(line)) continue;
        if (/^##\s+(1\.|2\.|3\.)\s/.test(line)) continue;
        if (/^##\s+双语重塑/.test(line)) continue;
        if (/^##\s+修复文本/.test(line)) continue;
        if (/^##\s+知识萃取/.test(line)) continue;
        if (/^##\s+双语对照版/.test(line)) continue;
        if (/^·\s*ReadShift/.test(line)) continue;
        if (/^#\s*(《张忠谋自传》|双语传记片段|为历史留下纪录|Preserving\s*History|附|自序|写传的)/.test(line)) continue;
        if (/^#\s*\d+页/.test(line)) continue;
        if (/^###\s*(📌|🎯|🌐|商业语汇提炼|修辞与逻辑赏析|外链知识窗|知识卡片)/.test(line)) continue;
        if (line.includes('<!-- PROCESSED -->')) continue;
        if (/以下是基于输入中英对照正文重新萃取的成果/.test(line)) continue;
        if (/^#\s*从文本中提取/.test(line)) continue;

            const hasCn = hasChinese(line);
            const hasEn = hasEnglish(line);

            if (hasCn && !hasEn) {
                if (!curBlock || curBlock.type !== 'cn') {
                    if (curBlock) sectionBlocks.push(curBlock);
                    curBlock = { type: 'cn', lines: [line] };
                } else {
                    curBlock.lines.push(line);
                }
            } else if (!hasCn && hasEn) {
                if (!curBlock || curBlock.type !== 'en') {
                    if (curBlock) sectionBlocks.push(curBlock);
                    curBlock = { type: 'en', lines: [line] };
                } else {
                    curBlock.lines.push(line);
                }
            } else if (hasCn && hasEn) {
                // Mixed line — check if it's a section title
                if (/^#{1,2}\s/.test(line) && line.length < 80) {
                    if (curBlock) sectionBlocks.push(curBlock);
                    curBlock = { type: 'title', lines: [line] };
                } else {
                    // Mixed content — try to split by language
                    const cnParts = [];
                    const enParts = [];
                    for (const ch of line) {
                        if (/\u4e00-\u9fff/.test(ch)) cnParts.push(ch);
                        else if (/[a-zA-Z]/.test(ch)) enParts.push(ch);
                    }
                    if (cnParts.length > 0 && enParts.length > 0) {
                        // Truly mixed line — output as CN
                        if (curBlock && curBlock.type === 'cn') {
                            curBlock.lines.push(line);
                        } else {
                            if (curBlock) sectionBlocks.push(curBlock);
                            curBlock = { type: 'cn', lines: [line] };
                        }
                    } else if (cnParts.length > 0) {
                        if (curBlock && curBlock.type === 'cn') {
                            curBlock.lines.push(line);
                        } else {
                            if (curBlock) sectionBlocks.push(curBlock);
                            curBlock = { type: 'cn', lines: [line] };
                        }
                    } else if (enParts.length > 0) {
                        if (curBlock && curBlock.type === 'en') {
                            curBlock.lines.push(line);
                        } else {
                            if (curBlock) sectionBlocks.push(curBlock);
                            curBlock = { type: 'en', lines: [line] };
                        }
                    }
                }
            }
            // else: no CN, no EN — skip
        }
        if (curBlock) sectionBlocks.push(curBlock);

        // Determine if this section has bilingual content
        const hasCnBlocks = sectionBlocks.some(b => b.type === 'cn');
        const hasEnBlocks = sectionBlocks.some(b => b.type === 'en');
        if (hasCnBlocks && hasEnBlocks) {
            pairSections.push(sectionBlocks);
        } else if (hasCnBlocks) {
            cnOnlySections.push(sectionBlocks);
        }
    }

    // Pair blocks within each bilingual section
    function pairBlocks(sectionBlocks) {
        const pairs = [];
        const cnOnly = [];
        let pendingCN = null;
        for (const b of sectionBlocks) {
            if (b.type === 'cn') {
                pendingCN = b.lines.join(' ');
            } else if (b.type === 'en' && pendingCN !== null) {
                pairs.push({ cn: pendingCN, en: b.lines.join(' ') });
                pendingCN = null;
            } else if (b.type === 'en') {
                // orphan EN without CN — skip
            }
        }
        if (pendingCN !== null) cnOnly.push(pendingCN);
        return { pairs, cnOnly };
    }

    const allPairs = [];
    for (const sb of pairSections) {
        const { pairs, cnOnly } = pairBlocks(sb);
        allPairs.push(...pairs);
        cnOnlySections.push([...cnOnly.map(t => ({ type: 'cn', lines: [t] }))]);
    }

    // ── build HTML ──────────────────────────────────────────────────────────
    let html = `\n`;

    for (const { cn, en } of allPairs) {
        const cnText = md.renderInline(cn)
            .replace(/<\/p>\s*<p[^>]*>.*?<\/p>/gs, '')
            .replace(/<\/p>\s*<p[^>]*>$/s, '')
            .replace(/^<p[^>]*>/, '')
            .replace(/<\/p>$/, '');
        const enText = md.renderInline(en)
            .replace(/<\/p>\s*<p[^>]*>.*?<\/p>/gs, '')
            .replace(/<\/p>\s*<p[^>]*>$/s, '')
            .replace(/^<p[^>]*>/, '')
            .replace(/<\/p>$/, '');
        html += `  <div class="bilingual-pair">\n`;
        html += `    <p class="cn-para">${wrapTerms(cnText, terms)}</p>\n`;
        html += `    <p class="en-para">${wrapTerms(enText, terms)}</p>\n`;
        html += `  </div>\n`;
    }

    for (const sectionBlocks of cnOnlySections) {
        for (const b of sectionBlocks) {
            if (b.type !== 'cn') continue;
            const text = md.renderInline(b.lines.join(' '))
                .replace(/<\/p>\s*<p[^>]*>.*?<\/p>/gs, '')
                .replace(/<\/p>\s*<p[^>]*>$/s, '')
                .replace(/^<p[^>]*>/, '')
                .replace(/<\/p>$/, '');
            html += `  <p class="cn-para">${wrapTerms(text, terms)}</p>\n`;
        }
    }

    // Knowledge cards
    const kcHtml = extractKnowledgeCards(content);
    if (kcHtml) html += kcHtml;

    return html;
}

// ── main ─────────────────────────────────────────────────────────────────────
let bodyContent = '';
for (const file of files) {
    const raw = fs.readFileSync(path.join(fullDir, file), 'utf8');
    bodyContent += processFile(file, raw) + '\n<hr class="page-divider">\n\n';
}

const htmlBody = md.render(bodyContent);
const fixedHtml = htmlBody
    .replace(/&lt;span class=['"]interactive-term['"]/g, '<span class="interactive-term">')
    .replace(/&lt;span /g, '<span ')
    .replace(/data-term=['"]/g, 'data-term="')
    .replace(/data-meaning=['"]/g, 'data-meaning="')
    .replace(/&lt;\/span&gt;/g, '</span>')
    .replace(/&lt;div class=['"]knowledge-card/g, '<div class="knowledge-card"')
    .replace(/&lt;\/div&gt;/g, '</div>')
    .replace(/&lt;p class=['"][^'"]*['"]/g, '<p class="')
    .replace(/&lt;\/p&gt;/g, '</p>')
    .replace(/&lt;hr class=['"]page-divider['"]/g, '<hr class="page-divider">')
    .replace(/&lt;h2 class=['"]page-heading['"]/g, '<h2 class="page-heading">');

const finalHtml = ejs.render(template, {
    title: '张忠谋自传 · 双语典藏版',
    body_content: fixedHtml,
    current_mode: 'Gemini 3.6 Flash + Agnes 2.5 Flash',
});

const outDir = path.join(__dirname, '..', 'output');
fs.writeFileSync(path.join(outDir, 'preview_book.html'), finalHtml, 'utf8');
console.log('\n✅ 已生成 v8 典藏排版: preview_book.html'
    + ` (${files.length} pages, ${totalTerms} terms, ${(finalHtml.length / 1024).toFixed(0)} KB)`);
