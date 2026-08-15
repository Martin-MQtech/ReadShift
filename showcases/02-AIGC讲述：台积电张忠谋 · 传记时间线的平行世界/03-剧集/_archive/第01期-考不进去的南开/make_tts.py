#!/usr/bin/env python3
"""
ReadShift 有声书 TTS 生成脚本
用法: python3 make_tts.py <zh|en>
读取对应文字稿, 跳过标题/音效/注释行, 逐段 edge-tts 合成, 段间插入静音后拼接为单文件。
"""
import re
import subprocess
import sys
import os
import glob
import shutil
import time

BASE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(BASE, "_tmp_audio")
os.makedirs(WORK, exist_ok=True)

VOICES = {
    "zh": "zh-CN-YunjianNeural",   # 沉稳男声
    "en": "en-US-ChristopherNeural",  # 沉稳美音男声
}
FILES = {
    "zh": os.path.join(BASE, "中文文字稿.md"),
    "en": os.path.join(BASE, "英文文字稿.md"),
}
OUT = {
    "zh": os.path.join(BASE, "中文音频.mp3"),
    "en": os.path.join(BASE, "英文音频.mp3"),
}
PAUSE = 0.7  # 段间静音秒数

def clean_segments(text: str):
    """提取可朗读段落, 去掉标题/音效/引用/分隔线; 清理 markdown 符号。"""
    lines = text.splitlines()
    segs = []
    cur = []
    for line in lines:
        s = line.strip()
        # 跳过标题/引用/分隔线/音效标记(中文【】与英文 [SFX]/[Narrator])
        if re.match(r"^#{1,6}\s", s):
            continue
        if s.startswith(">"):
            continue
        if re.match(r"^-{3,}$", s):
            continue
        if re.match(r"^【|^\[SFX|^\[Narrator|^\[主叙述者", s):
            continue
        if not s:
            if cur:
                segs.append(" ".join(cur))
                cur = []
            continue
        cur.append(s)
    if cur:
        segs.append(" ".join(cur))
    out = []
    for s in segs:
        s = s.replace("**", "").replace("__", "")
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            out.append(s)
    return out

def tts(text: str, voice: str, out_path: str):
    for attempt in range(4):
        try:
            subprocess.run(
                ["edge-tts", "--voice", voice, "--text", text, "--write-media", out_path],
                check=True, capture_output=True,
            )
            return
        except subprocess.CalledProcessError:
            if attempt == 3:
                raise
            time.sleep(2 + attempt * 2)

def silence(seconds: float, out_path: str, sr: int = 24000):
    n = int(sr * seconds)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=mono",
         "-t", f"{seconds}", "-q:a", "4", out_path],
        check=True, capture_output=True,
    )

def concat(parts, out_path):
    with open(os.path.join(WORK, "list.txt"), "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
         os.path.join(WORK, "list.txt"), "-c:a", "libmp3lame", "-q:a", "3", out_path],
        check=True, capture_output=True,
    )

def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "zh"
    if lang not in VOICES:
        raise SystemExit("lang must be zh or en")
    text = open(FILES[lang], encoding="utf-8").read()
    segs = clean_segments(text)
    print(f"[{lang}] 提取 {len(segs)} 个朗读段落")
    parts = []
    sil = os.path.join(WORK, "pause.mp3")
    silence(PAUSE, sil)
    for i, seg in enumerate(segs, 1):
        p = os.path.join(WORK, f"seg_{i:03d}.mp3")
        print(f"  [{i}/{len(segs)}] {seg[:28]}...")
        tts(seg, VOICES[lang], p)
        parts.append(p)
        parts.append(sil)
    print(f"[{lang}] 拼接 {len(parts)} 个片段 -> {OUT[lang]}")
    concat(parts, OUT[lang])
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", OUT[lang]],
        capture_output=True, text=True,
    ).stdout.strip()
    print(f"[{lang}] 完成: {OUT[lang]}  时长 {float(dur):.1f}s")
    shutil.rmtree(WORK, ignore_errors=True)

if __name__ == "__main__":
    main()
