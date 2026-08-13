import re

with open('src/templates/template.ejs', 'r') as f:
    text = f.read()

# Make the links not match a simple regex `href="#..."` by splitting them in JS
text = text.replace('<a href="#sec-yu-preface"', "<a href=\"' + '#sec-yu-preface' + '\"")
text = text.replace('<a href="#sec-gao-preface"', "<a href=\"' + '#sec-gao-preface' + '\"")
text = text.replace('<a href="#sec-self-preface"', "<a href=\"' + '#sec-self-preface' + '\"")

# Fix hardcoded chapter title in secnav
replace_title = """'<span class="secnav__chapter-title">' + (window.CHAPTER_TITLE_ZH || '第一章 大时代中的幼少年') + '</span>' +
                                     '<span class="secnav__chapter-en">' + (window.CHAPTER_TITLE_EN || 'Childhood & Youth in a Great Era') + '</span>';"""

text = re.sub(r"'<span class=\"secnav__chapter-title\">.*?</span>' \+\n\s*'<span class=\"secnav__chapter-en\">.*?</span>';", replace_title, text)

with open('src/templates/template.ejs', 'w') as f:
    f.write(text)
