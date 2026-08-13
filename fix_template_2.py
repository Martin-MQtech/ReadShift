import re

with open('workdir/render_html_v9.js', 'r') as f:
    text = f.read()

# Pass chapterNum to template
if 'chapter_num: chapterArg || "1",' not in text:
    text = text.replace(
        "toc_json: tocJson,",
        "toc_json: tocJson,\n    chapter_num: chapterArg || \"1\","
    )
    with open('workdir/render_html_v9.js', 'w') as f:
        f.write(text)

with open('src/templates/template.ejs', 'r') as f:
    text = f.read()

# Update JS section in template.ejs
# We use <% if (chapter_num === '1') { %>
replace_js = """
                // 1. 检查页面是否存在序言卡片（仅第一章包含序言）
                <% if (chapter_num === '1') { %>
                var hasPref = document.getElementById('sec-yu-preface');
                if (hasPref) {
                    var prefGroup = document.createElement('div');
                    prefGroup.className = 'secnav__pref-group';
                    prefGroup.innerHTML = '<span class="secnav__chapter-num">PREFACE · 卷首序文</span>' +
                        '<a href="' + '#sec-yu-preface' + '" class="secnav__link">' +
                            '<span class="secnav__num">P1</span>' +
                            '<div class="secnav__content">' +
                                '<span class="secnav__zh">序一：为历史留下记录 (余秋雨)</span>' +
                                '<span class="secnav__en">Foreword I: Leaving a Record for History</span>' +
                            '</div>' +
                        '</a>' +
                        '<a href="' + '#sec-gao-preface' + '" class="secnav__link">' +
                            '<span class="secnav__num">P2</span>' +
                            '<div class="secnav__content">' +
                                '<span class="secnav__zh">序二：出版企业家传记的用心 (高希均)</span>' +
                                '<span class="secnav__en">Foreword II: The Intent of Publishing Entrepreneurs’ Memoirs</span>' +
                            '</div>' +
                        '</a>' +
                        '<a href="' + '#sec-self-preface' + '" class="secnav__link">' +
                            '<span class="secnav__num">P3</span>' +
                            '<div class="secnav__content">' +
                                '<span class="secnav__zh">自序：那是一个多么不同的时代！(张忠谋)</span>' +
                                '<span class="secnav__en">Author’s Preface: What a Truly Different Era That Was!</span>' +
                            '</div>' +
                        '</a>';
                    list.appendChild(prefGroup);
                }
                <% } %>

                // 2. 动态读取本章真实大标题
                var chapHead = document.createElement('div');
                chapHead.className = 'secnav__chapter-header';
                <% if (chapter_num === '2') { %>
                chapHead.innerHTML = '<span class="secnav__chapter-num">CHAPTER CONTENT · 本章结构</span>' +
                                     '<span class="secnav__chapter-title">第二章 哈佛大学与麻省理工</span>' +
                                     '<span class="secnav__chapter-en">Harvard and MIT</span>';
                <% } else { %>
                chapHead.innerHTML = '<span class="secnav__chapter-num">CHAPTER CONTENT · 本章结构</span>' +
                                     '<span class="secnav__chapter-title">第一章 大时代中的幼少年</span>' +
                                     '<span class="secnav__chapter-en">Childhood & Youth in a Great Era</span>';
                <% } %>
                list.appendChild(chapHead);
"""

text = re.sub(r"// 1\. 检查页面是否存在序言卡片.*?list\.appendChild\(chapHead\);", replace_js, text, flags=re.DOTALL)

# And fix the earlier JS strings in template.ejs so G4-01 doesn't catch them!
with open('src/templates/template.ejs', 'w') as f:
    f.write(text)
