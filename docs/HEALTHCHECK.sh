#!/usr/bin/env bash
# ReadShift D1(source/*.md) 资产健康体检
# 用法:
#   bash docs/HEALTHCHECK.sh                # 检查全部六章
#   bash docs/HEALTHCHECK.sh 3              # 只检查第三章
#   bash docs/HEALTHCHECK.sh 2,4            # 检查第二、四章
# 目的: 开工前/合成本前, 把历史脏数据(未闭合标签、占位符、多空行、孤立章名)拦下。
set -euo pipefail

cd "$(dirname "$0")/.."
SCOPE="${1:-1,2,3,4,5,6}"
IFS=',' read -ra CHS <<< "$SCOPE"

overall=0
for cn in "${CHS[@]}"; do
  cnn=$(printf "0%s" "$cn")
  dir=$(ls -d output/chapters/chap-$cnn-* 2>/dev/null | head -1) || true
  [ -z "$dir" ] && { echo "章$cn: 目录不存在，跳过"; continue; }
  src="$dir/source"
  echo "===== 章$cn ($(basename "$dir")) ====="
  python3 - "$src" <<'PYEOF'
import re, glob, sys
src=sys.argv[1]
files=sorted(glob.glob(src+"/page_*.md"))
issues=0
for f in files:
    t=open(f,encoding='utf-8').read(); name=f.split("/")[-1]
    # 1) div/span 闭合(栈)
    st=[]
    for m in re.finditer(r'<(/?)\s*(div|span)\b', t):
        if m.group(1)=='/' and st and st[-1]==m.group(2): st.pop()
        elif m.group(1)!='/': st.append(m.group(2))
    if st: print(f"  ✗ {name}: 未闭合标签 {st[:3]}"); issues+=1
    # 2) rhetoric-note 闭合
    if len(re.findall(r'<span class="rhetoric-note">',t)) != len(re.findall(r'<span class="rhetoric-note">[\s\S]*?</span>\s*</span>',t)):
        print(f"  ✗ {name}: rhetoric-note 未闭合"); issues+=1
    # 3) 占位符
    for ph in ["英文翻译。","TBD","TODO","待补充"]:
        if ph in t: print(f"  ✗ {name}: 占位符[{ph}]"); issues+=1
    # 4) 多空行
    if re.search(r"\n{3,}",t): print(f"  ✗ {name}: 连续空行"); issues+=1
    # 5) 孤立章名大标题(首段前)
    first=next((l for l in t.split('\n') if l.strip()), '')
    if re.match(r'^#?\s*(第[一二三四五六]章|附录)\s*$', first.strip()):
        print(f"  ✗ {name}: 正文前孤立章名[{first.strip()}]"); issues+=1
    # (繁体检测不在此处理：宽度范围易误报，最终以 QA G2-02「全书规范简体」为准)
print(f"章{'':>0} 体检: {'✓ 干净' if issues==0 else f'✗ {issues} 处问题'}")
PYEOF
  [ $? -ne 0 ] && overall=1
done
echo ""
echo "=== 体检完成: ${overall:-0} 处错误 ==="
[ "$overall" -eq 0 ] || exit 1
