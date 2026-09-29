# ffmpeg 剪辑流水线（LibTV 短片统一剪辑）

> 跨项目通用知识包。LibTV CLI 只负责"单镜出片"；把一堆分镜片段融成一支成片（转场 + 配乐 + 旁白 + 字幕 + 封面 + 缩略图）全靠本地 ffmpeg。本文给**可直接复制的 Python(imageio-ffmpeg) 模板**，照此还原成完整可跑流水线。
>
> 案例均取自"30 岁生日短片"（32 段 2D 绘本动画，5'09"，光/门/手转场母题）。**案例 = 举例，不是约束**；方法论本身与项目无关。

---

## 0. 心智模型：为什么要本地剪

| 阶段 | 工具 | 产物 |
|---|---|---|
| 单镜生成 | LibTV CLI（StarVideo 2.0） | N 个独立 MP4；仅在实际输入流含音频时才可走音频复用路线 |
| **统一剪辑** | **本地 ffmpeg / PIL** | 1 支成片（转场无缝、配乐连续、字幕封面齐全） |

LibTV 的 `video-clip` 终剪节点能力弱、时间线难精确控；**真正的剪辑全部下沉到本地**。本地剪的好处：可逐帧调 offset、可逐段补救穿帮、可换 BGM 重渲染、零积分消耗、可复现。

核心难点就两条，本文围绕它们展开：

1. **转场 offset 累加**——`xfade` 的每个 offset 必须用**纯视频时长**累加（不是片段简单首尾相接），算错就错位。
2. **音视频不同步**——AAC 编码每段补 padding，按音频时长算 offset 会越往后越偏，**视频走 xfade、音频单独走 acrossfade**。

---

## 1. 取 ffmpeg（零安装依赖）

不依赖系统 PATH 里的 ffmpeg，用 `imageio-ffmpeg` 自带的静态二进制，跨机器稳定。

```python
import imageio_ffmpeg
ff = imageio_ffmpeg.get_ffmpeg_exe()   # 返回打包好的 ffmpeg.exe 绝对路径
# 之后所有 ffmpeg 调用都用 ff，不写 "ffmpeg"
```

```bash
pip install imageio-ffmpeg pillow numpy
# opencv-python 仅在需要逐帧改图/拼帧时装；纯剪辑用不到
```

> 注意：`imageio-ffmpeg` 自带的 ffmpeg **不含 `ffprobe`**。探时长不要调 ffprobe，改用 `ffmpeg -i` 解析 stderr（见下节）。

---

## 2. 探时长（解析 `ffmpeg -i` 的 stderr）

`ffmpeg -i <file>`（不给输出）会把元信息打到 **stderr**，里面有 `Duration: HH:MM:SS.ss`。正则抓出来转秒。

```python
import subprocess, re

def probe_duration(path, ff):
    """返回视频时长（秒，float）。解析 ffmpeg -i 的 stderr。"""
    p = subprocess.run(
        [ff, "-hide_banner", "-i", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    # ffmpeg 没有输出文件时返回码非 0，但 stderr 里有 Duration，正常
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
    if not m:
        raise RuntimeError(f"无法解析时长: {path}\n{p.stderr[-500:]}")
    h, mm, ss = m.groups()
    return int(h) * 3600 + int(mm) * 60 + float(ss)
```

> **关键：offset 累加必须用这里探到的纯视频时长**（见第 4 节踩坑）。一次性探完所有片段缓存成列表 `ds = [probe_duration(c, ff) for c in clips]`，后面 xfade/acrossfade 都复用它。

---

## 3. 规格统一（xfade 的前置铁律）

`xfade` / `concat` filter **要求所有输入流参数完全一致**（分辨率、帧率、像素格式、SAR、音频采样率/声道）。Seedance 出的片段分辨率/帧率可能有细微差异，**先逐段转码成统一规格**，再进 xfade 链。不统一会直接报错或画面跳。

```python
import subprocess, os

def normalize(src, dst, ff, w=1280, h=720, fps=24, keep_audio=True):
    """把单段统一成 1280x720 / 24fps / yuv420p / libx264。keep_audio 时统一 48k 立体声。"""
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"   # letterbox 兜底，防比例不一
          f"setsar=1,fps={fps},format=yuv420p")
    cmd = [ff, "-y", "-i", src,
           "-vf", vf,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p"]
    if keep_audio:
        cmd += ["-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k"]
    else:
        cmd += ["-an"]
    cmd += [dst]
    subprocess.run(cmd, check=True)
    return dst
```

要点：
- **`scale + pad + setsar=1`**：强制统一画幅和像素宽高比，xfade 才不报错。
- **`fps=24`**：帧率必须统一，否则 xfade 的时间轴对不齐。
- **`format=yuv420p`**：统一像素格式，兼容性最好（QuickTime/微信/浏览器都能播）。
- **`libx264 -preset veryfast -crf 20`**：veryfast 渲染快，crf20 视觉无损够用；定稿想更小可 crf18~20 + preset slow。
- **`-ar 48000 -ac 2`**：保留音轨时统一音频规格，acrossfade 才不报错。

---

## 4. xfade 转场链（核心：offset 累加公式）

`xfade` 一次只接两路。N 段要**链式**：clip0 与 clip1 交叠 → 结果与 clip2 交叠 …… 每次 xfade 吃掉 `T` 秒（两段重叠时长），所以**时间轴会越缩越短**，offset 必须累加补偿。

### 4.1 offset 公式（背下来）

设转场时长 `T`（如 0.8s），各段纯视频时长 `ds[0..n-1]`：

```
第 1 个 xfade（clip0 × clip1）：offset = ds[0] - T
随后维护一个累计可见时长 cum：
    cum = ds[0]                       # 第 0 段铺满
    对 i = 1 .. n-1：
        off_i = cum - T               # 本次 xfade 的 offset
        cum   = cum + ds[i] - T       # 加上本段、再扣掉这次交叠
```

直觉：每次交叠让总时长少 `T`，所以下一个 offset 要在"上一段结束点"前移 `T` 开始淡入。**off 用纯视频时长算，错一点点后面全偏**。

### 4.2 转场类型选择（母题驱动）

| `transition=` | 观感 | 用在哪种剪辑点（案例） |
|---|---|---|
| `dissolve` / `fade` | 柔和叠化 | 默认通用转场、同场景内推进 |
| `fadewhite` | 闪白 | **时空跳跃**（童年→中学、城市切换）——"光"母题 |
| `fadeblack` | 渐黑再起 | **昼→夜 / 段落收束**——案例 shot4 黄昏渐暗接夜路 |
| `wipeleft`/`slideup`/`circleopen` 等 | 几何擦除 | 需要明确"翻页感"时；绘本风慎用，易出戏 |

> 转场母题：把"光/门/手"做成贯穿全片的转场语言——光出口用 `fadewhite`，昼夜切换用 `fadeblack`，其余 `dissolve`。让每段结尾留"转场钩子"（望窗晨光 / 推门 / 伸手），剪辑时转场就有落点。

### 4.3 完整 filter_complex 拼接（纯视频，先不管音频）

```python
import subprocess

def build_xfade_filter(n, ds, T=0.8, trans="dissolve"):
    """
    生成纯视频 xfade 链的 filter_complex 字符串和最终输出 label。
    n: 段数；ds: 各段纯视频时长列表；T: 转场秒；trans: 转场类型（可传 list 逐点不同）。
    """
    if isinstance(trans, str):
        trans = [trans] * (n - 1)        # 每个转场点可单独指定类型
    parts = []
    cum = ds[0]
    prev = "0:v"                          # 第 0 段视频流
    for i in range(1, n):
        off = cum - T                     # ← 核心 offset 公式
        out = f"vx{i}"
        parts.append(
            f"[{prev}][{i}:v]"
            f"xfade=transition={trans[i-1]}:duration={T}:offset={off:.3f}"
            f"[{out}]"
        )
        prev = out
        cum = cum + ds[i] - T             # 累计可见时长更新
    return ";".join(parts), prev          # prev 是最终视频 label

def render_xfade(clips, ds, ff, out_path, T=0.8, trans="dissolve"):
    """把已 normalize 的 clips 用 xfade 链拼成一支（仅视频；音频见第 5 节）。"""
    n = len(clips)
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    fc, vlabel = build_xfade_filter(n, ds, T, trans)
    cmd = [ff, "-y", *inputs,
           "-filter_complex", fc,
           "-map", f"[{vlabel}]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-an",   # 先不带音；音频单独处理
           out_path]
    subprocess.run(cmd, check=True)
    return out_path
```

> N 段会生成 N-1 个 `xfade` 节点，filter 链很长但结构机械，照公式生成即可。**先单独渲染纯视频确认转场无错位**，再叠音频，调试快。

---

## 5. 音频两条路线

**铁律先行（踩坑根因）**：AAC 编码会给每段补 ~80ms encoder padding/delay，**逐段累积**会让后半段的音频比视频慢半拍——所以**绝不能用音频时长去算 offset**。正确做法：**视频 offset 用纯视频时长（第 4 节），音频用 `acrossfade` 自己交叠**，两者 `T` 取同值即可天然同步，无需对音频做 offset 计算。

### 路线 ① 仅在每段实际有音频流时复用音轨

【历史经验，未重测】若 Seedance 片源实际带有环境音轨，可将它作为素材，让它随 xfade 同步交叉淡化；不要假定 `enableSound=off` 仍会生成音轨。导出前先检查输入是否真的有音频流，再决定是否保留音轨。

`acrossfade` 与 `xfade` 一样链式两两交叠，`d=T` 与视频转场同值：

```python
def build_audio_acrossfade(n, T=0.8):
    """仅用于已检查为每段都有音频流的输入：链式 acrossfade，d 与视频 xfade 的 T 同值。"""
    parts = []
    prev = "0:a"
    for i in range(1, n):
        out = f"ax{i}"
        # acrossfade 不需要 offset：它直接把前一路尾 d 秒与后一路头 d 秒交叠
        parts.append(f"[{prev}][{i}:a]acrossfade=d={T}:c1=tri:c2=tri[{out}]")
        prev = out
    return ";".join(parts), prev
```

把视频链和音频链拼进同一个 `-filter_complex`，各自 map：

```python
def render_xfade_with_self_audio(clips, ds, ff, out_path, T=0.8, trans="dissolve"):
    n = len(clips)
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    vfc, vlabel = build_xfade_filter(n, ds, T, trans)
    afc, alabel = build_audio_acrossfade(n, T)
    fc = vfc + ";" + afc
    cmd = [ff, "-y", *inputs,
           "-filter_complex", fc,
           "-map", f"[{vlabel}]", "-map", f"[{alabel}]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
           "-pix_fmt", "yuv420p",
           out_path]
    subprocess.run(cmd, check=True)
    return out_path
```

### 路线 ② 连续 BGM（铺一首/两首贯穿）

成片想要统一情绪线时，用整段 BGM 覆盖全部分镜音。两段 BGM 在**情绪转折点** `acrossfade` 交叉，整首首尾 `afade` 淡入淡出。

```python
def build_bgm_track(bgm_a, bgm_b, ff, out_a_path, total_dur,
                    cross_at, cross_d=8.0, fade_in=2.0, fade_out=3.0):
    """
    两段 BGM 在 cross_at 秒处 acrossfade=d=cross_d 交叉，整轨首尾 afade。
    total_dur: 成片总时长；cross_at: A→B 交叉中心点（情绪转折）。
    """
    # A 取到交叉点+半个交叠，B 从 0 起；acrossfade 自动对齐尾头
    fc = (
        f"[0:a]atrim=0:{cross_at + cross_d:.3f},asetpts=PTS-STARTPTS[a0];"
        f"[1:a]asetpts=PTS-STARTPTS[a1];"
        f"[a0][a1]acrossfade=d={cross_d}:c1=tri:c2=tri[mix];"
        f"[mix]atrim=0:{total_dur:.3f},"
        f"afade=t=in:st=0:d={fade_in},"
        f"afade=t=out:st={total_dur - fade_out:.3f}:d={fade_out}[out]"
    )
    cmd = [ff, "-y", "-i", bgm_a, "-i", bgm_b,
           "-filter_complex", fc, "-map", "[out]",
           "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
           out_a_path]
    subprocess.run(cmd, check=True)
    return out_a_path

def mux_video_with_bgm(silent_video, bgm_track, ff, out_path):
    """把纯视频成片（第 4 节 render_xfade 出的 -an 版）与连续 BGM 合轨。"""
    cmd = [ff, "-y", "-i", silent_video, "-i", bgm_track,
           "-map", "0:v", "-map", "1:a",
           "-c:v", "copy", "-c:a", "aac", "-shortest",
           out_path]
    subprocess.run(cmd, check=True)
    return out_path
```

> 旁白：另起一条 narration 轨（TTS 或真人录音），用 `amix` 与 BGM 混合并把 BGM 在旁白段 ducking（`sidechaincompress` 或简单分段降增益）。混轨时 BGM 音量压到旁白下方约 -8~-12dB。

### 两路线对比

| | ① 复用已检查存在的音轨 | ② 连续 BGM |
|---|---|---|
| 工作量 | 小（不另找音乐） | 中（选曲+混音+旁白 ducking） |
| 观感 | 氛围真实、但情绪线碎 | 情绪统一、更"成片" |
| 同步风险 | 靠 acrossfade 同步，无 offset 计算 | BGM 独立轨，无逐段同步问题 |
| 案例 | 【历史经验，未重测】v1 720p 预览在输入流检查通过后使用此路 | 备用 `bgm_partA/B.mp3` 走此路 |

---

## 6. 封面片头（loop 静图当第 0 段）

把一张封面 PNG 用 `-loop 1 -t` 变成定长视频段，`fade=t=in` 淡入，**当作第 0 段并入 xfade 链**（它也要先 `normalize` 成统一规格、也要进 `ds` 列表参与 offset 累加）。

```python
def cover_to_clip(cover_png, dst, ff, w=1280, h=720, fps=24, t=2.0, fin=0.5):
    """封面静图 → t 秒视频段，开头 fin 秒淡入。规格与正片一致，可直接进 xfade 链。"""
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},"
          f"format=yuv420p,fade=t=in:st=0:d={fin}")
    cmd = [ff, "-y", "-loop", "1", "-i", cover_png, "-t", str(t),
           "-vf", vf,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-an", dst]
    subprocess.run(cmd, check=True)
    return dst
```

> 把它放在 `clips[0]`、时长放 `ds[0]`，xfade 链第一个转场就是"封面淡出→第一镜淡入"。静图段没有音轨——走路线① 时给它补一段静音（`-f lavfi -i anullsrc`）或在 acrossfade 链里跳过它。

---

## 7. 片尾字幕卡（PIL 排版 + ffmpeg 定长淡入淡出）

字幕卡两步：**PIL 把多行文字画到黑场 PNG**（精确控字体/字号/居中/行距），再 **ffmpeg 把 PNG 变定长视频段**（淡入+停留+淡出），当最后一段并入 xfade 链或直接 concat。

### 7.1 PIL 渲染字幕图（中文必须指定中文字体）

```python
from PIL import Image, ImageDraw, ImageFont

def make_endcard_png(lines, out_png, w=1280, h=720,
                     bg=(8, 8, 10), fg=(255, 244, 228),
                     font_path=r"C:\Windows\Fonts\msyhbd.ttc",  # 微软雅黑 Bold
                     font_size=46, line_gap=28):
    """多行文字居中画到黑场。bg 近黑、fg 暖白。中文路径 PIL 直接支持。"""
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)   # 必须传中文字体，否则中文变方块
    # 量每行高度，算总高做垂直居中
    sizes = []
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        sizes.append((bbox[2] - bbox[0], bbox[3] - bbox[1]))
    total_h = sum(hh for _, hh in sizes) + line_gap * (len(lines) - 1)
    y = (h - total_h) // 2
    for (lw, lh), ln in zip(sizes, lines):
        x = (w - lw) // 2                              # 水平居中
        draw.text((x, y), ln, font=font, fill=fg)
        y += lh + line_gap
    img.save(out_png)
    return out_png
```

> 字体备选：标题 `msyhbd.ttc`（雅黑粗）、正文 `msyh.ttc`（雅黑常规）、书法感 `STKAITI.TTF`（华文楷体）。**一定显式给字体路径**——不给字体或给英文字体，中文会渲染成空白方块。

### 7.2 字幕图 → 定长视频段（淡入·停留·淡出）

```python
def endcard_to_clip(card_png, dst, ff, w=1280, h=720, fps=24,
                    t=6.0, fin=1.0, fout_d=1.2):
    """字幕卡 PNG → t 秒段，开头淡入 fin，结尾 fout_d 淡出（st = t - fout_d）。"""
    fout_st = t - fout_d
    vf = (f"scale={w}:{h},setsar=1,fps={fps},format=yuv420p,"
          f"fade=t=in:st=0:d={fin},"
          f"fade=t=out:st={fout_st:.2f}:d={fout_d}")
    cmd = [ff, "-y", "-loop", "1", "-i", card_png, "-t", str(t),
           "-vf", vf,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-an", dst]
    subprocess.run(cmd, check=True)
    return dst
```

> 案例参数：黑场 `(8,8,10)`、暖白字 `(255,244,228)`、6s 停留、淡入 1.0s、淡出 1.2s（`st=4.8`）。字幕卡通常直接 `concat` 接在成片尾部（不必 xfade，渐黑收束更干净）；要更柔可把它也并入 xfade 链用 `fadeblack`。

---

## 8. 嵌入缩略图（mp4 封面，文件管理器/播放器预览图）

把封面 PNG 作为附加视频流嵌进 mp4，标 `attached_pic`——Windows 资源管理器、多数播放器会拿它当缩略图。流拷贝，秒级完成。

```python
def embed_thumbnail(film_mp4, cover_png, out_mp4, ff):
    """给 mp4 嵌入封面缩略图（attached_pic）。-c copy 不重编码。"""
    cmd = [ff, "-y", "-i", film_mp4, "-i", cover_png,
           "-map", "0", "-map", "1:v",
           "-c", "copy",
           "-disposition:v:1", "attached_pic",
           out_mp4]
    subprocess.run(cmd, check=True)
    return out_mp4
```

> 缩略图 PNG 最好与片头封面同图（一致性），尺寸不必等于视频分辨率。若播放器不认，确认输出容器是 mp4/mov（mkv 的封面机制不同）。

---

## 9. 局部修补（不重渲全片，只救坏的那一段）

成片定稿后发现某段穿帮，**绝不重抽整片**。两类常用补救：

### 9.1 掐头去尾（切掉穿帮的格号/字幕渗透帧）

九宫格格号数字、单据文字常被 Seedance 照抄进画面前/后几帧。直接 `-ss`/`-to` 切掉那几帧（**`-ss` 放 `-i` 前 = 快速 seek**）：

```python
def trim_segment(src, dst, ff, start=0.0, end=None):
    """掐掉 [0,start) 和 (end, 末尾]。-ss 在 -i 前用关键帧快切，配 -c copy 极快。
       要精确到非关键帧或切完进 xfade，请去掉 -c copy 让其重编码。"""
    cmd = [ff, "-y", "-ss", f"{start:.3f}"]
    if end is not None:
        cmd += ["-to", f"{end:.3f}"]
    cmd += ["-i", src,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", dst]
    subprocess.run(cmd, check=True)
    return dst
```

> 案例：把开头 1.5s（带格号的渐入帧）切掉用 `-ss 1.5`。**切完时长变了，记得用第 2 节重新探时长更新 `ds`，否则 offset 全错。**

### 9.2 尾段续拍拼接（原片一帧不改，只在尾部接 4s）

某镜结尾太短/收得突兀，用 LibTV `singleImage2video` 拿该镜**末帧**续拍 4s，再用 **concat demuxer** 接回原片，接缝处一个短 `xfade 0.3` 缝合。前段一帧不改，避免重渲损质。

```python
def extract_last_frame(src, png, ff):
    """抽取末帧做续拍首帧（喂回 LibTV singleImage2video）。"""
    dur = probe_duration(src, ff)
    cmd = [ff, "-y", "-ss", f"{max(0, dur - 0.05):.3f}", "-i", src,
           "-frames:v", "1", "-q:v", "2", png]
    subprocess.run(cmd, check=True)
    return png

def stitch_tail(orig, tail, dst, ff, T=0.3):
    """仅在 orig/tail 都检查到音频流时，原片与续拍用 xfade=0.3 + acrossfade 缝合。"""
    d0 = probe_duration(orig, ff)
    off = d0 - T
    fc = (f"[0:v][1:v]xfade=transition=dissolve:duration={T}:offset={off:.3f}[v];"
          f"[0:a][1:a]acrossfade=d={T}:c1=tri:c2=tri[a]")
    cmd = [ff, "-y", "-i", orig, "-i", tail,
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-ar", "48000", "-ac", "2",
           "-pix_fmt", "yuv420p", dst]
    subprocess.run(cmd, check=True)
    return dst
```

> 纯无损拼接（同编码参数、无转场）可用 concat demuxer：写一个 `list.txt`（每行 `file '绝对路径'`）→ `ff -f concat -safe 0 -i list.txt -c copy out.mp4`。要转场就走上面 `stitch_tail`。

---

## 10. 中文路径处理（Windows 必踩）

| 工具 | 中文路径支持 | 写法 |
|---|---|---|
| **ffmpeg（subprocess）** | OK | 路径作为 `subprocess.run` 列表元素传入，**不手动拼 shell 字符串**（用 list 形式免转义） |
| **PIL** | OK，直接支持 | `Image.open(中文路径)` / `img.save(中文路径)` 正常 |
| **cv2（OpenCV）** | ✗ `imread`/`imwrite` 读不了中文路径 | 用 `imdecode`/`imencode` 绕（见下） |

```python
import cv2, numpy as np

def cv_imread(path):
    """cv2 读中文路径：先用 numpy 读字节再 imdecode。"""
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)

def cv_imwrite(path, img, ext=".png"):
    """cv2 写中文路径：imencode 后 tofile。"""
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok
```

> ffmpeg 调用永远用 **list 形式的 `subprocess.run([...])`**，让 Python 处理参数传递；别用 `shell=True` 拼字符串（中文+空格路径会炸）。PIL 渲字幕、读封面都没问题。只有动到 OpenCV（逐帧改图/拼帧）才需要 imdecode 绕路。

---

## 11. 拼装自检（手写镜头序列必查）

手写镜头序列极易笔误——漏一镜、重复一镜、顺序错。**拼装后必须核对**，不然成片时长对不上才发现已经晚了。

```python
def sanity_check(clips, expected_count=None, expected_total=None, ds=None, tol=2.0):
    """拼装前自检：段数、序号连续性、（可选）总时长。"""
    n = len(clips)
    print(f"段数 = {n}" + (f"（预期 {expected_count}）" if expected_count else ""))
    assert expected_count is None or n == expected_count, \
        f"段数不符：{n} != {expected_count}（漏镜或重复镜？）"
    # 文件名里的序号连续性检查（按你的命名规则改正则）
    import re
    nums = [int(m.group(1)) for c in clips if (m := re.search(r"shot(\d+)", c))]
    if nums:
        miss = sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
        dup = sorted({x for x in nums if nums.count(x) > 1})
        if miss: print(f"⚠ 缺序号: {miss}")
        if dup:  print(f"⚠ 重复序号: {dup}")
    if ds and expected_total:
        # xfade 后总时长 ≈ Σds - (n-1)*T；这里只校验原始 Σds 量级
        s = sum(ds)
        print(f"原始 Σ时长 = {s:.1f}s（预期成片 ≈ {expected_total:.1f}s）")
        assert abs(s - expected_total) < tol + (n - 1) * 0.8, "总时长异常，回查镜头序列"
    print("自检通过")
```

> 案例教训：拼片脚本手写序列漏了 15、重复了 16，成片时长和预估对不上才回查发现。**段数 + 序号连续性 + 总时长**三个量级对得上再渲染。

---

## 12. 端到端串联（把上面拼成一条流水线）

```python
import os
import imageio_ffmpeg

ff = imageio_ffmpeg.get_ffmpeg_exe()
PROJ = os.environ.get("PROJ_DIR", ".")   # 你的项目根（建议用环境变量，勿硬编码绝对路径）
WORK = os.path.join(PROJ, "work")        # 中间产物目录
os.makedirs(WORK, exist_ok=True)

# 0) 原始分镜片段（按序号排好；务必自检）
raw = [os.path.join(PROJ, "clips", f"shot{i:02d}.mp4") for i in range(1, 31)]

# 1) 先检查每个输入流；仅当全部都有音频流时才保留音频走路线①
norm = []
for i, c in enumerate(raw):
    d = os.path.join(WORK, f"n{i:02d}.mp4")
    normalize(c, d, ff, w=1280, h=720, fps=24, keep_audio=True)
    norm.append(d)

# 2) 封面段 + 字幕卡段
cover = cover_to_clip(os.path.join(WORK, "cover.png"), os.path.join(WORK, "cover.mp4"), ff, t=2.0)
make_endcard_png(["片尾主标题", "片尾副标题/祝福语"], os.path.join(WORK, "end.png"))
endcard = endcard_to_clip(os.path.join(WORK, "end.png"), os.path.join(WORK, "end.mp4"), ff, t=6.0)

# 3) 组装最终序列（封面 + 正片 + 字幕卡）并自检
clips = [cover] + norm + [endcard]
ds = [probe_duration(c, ff) for c in clips]        # ← offset 用这个纯视频时长
sanity_check(clips, expected_count=len(raw) + 2)

# 4) xfade；只有上一步确认每段都有音频流才执行下列 self-audio 调用，否则改走 BGM 路线或无音频导出
trans = ["dissolve"] * (len(clips) - 1)
trans[0] = "fadewhite"        # 封面→第一镜：闪白开场
trans[-1] = "fadeblack"       # 末镜→字幕卡：渐黑收束
film_silentaudio = render_xfade_with_self_audio(
    clips, ds, ff, os.path.join(WORK, "film_core.mp4"), T=0.8, trans=trans)

# 5) 嵌缩略图出定稿
final = embed_thumbnail(film_silentaudio, os.path.join(WORK, "cover.png"),
                        os.path.join(WORK, "成片_v1.mp4"), ff)
print("done:", final)
```

> 想换连续 BGM：第 4 步改用 `render_xfade(...)`（`-an` 纯视频）→ `build_bgm_track(...)` → `mux_video_with_bgm(...)` → 再 `embed_thumbnail`。

---

## 速查总表

| 任务 | 关键命令/函数 | 一句话踩坑 |
|---|---|---|
| 取 ffmpeg | `imageio_ffmpeg.get_ffmpeg_exe()` | 自带二进制无 ffprobe |
| 探时长 | `ffmpeg -i` 解析 stderr `Duration:` | **offset 必须用纯视频时长** |
| 规格统一 | `scale+pad+setsar=1,fps,format=yuv420p` + libx264 veryfast crf20 | 不统一 xfade 直接报错 |
| 转场链 | `xfade`，`off = cum - T; cum += ds[i] - T` | offset 累加错一点后面全偏 |
| 转场类型 | dissolve / fadewhite(时空跳) / fadeblack(昼→夜) | 母题=光/门/手 |
| 音频① | 输入流检查确认每段都有音频后，`acrossfade=d=T`（同 T） | 不假定 `enableSound=off` 仍有音轨；缺流时改用音频②或无音频导出 |
| 音频② | 两段 BGM `acrossfade=d=8` + 首尾 afade | **音频单独走，不参与 offset 计算** |
| 封面 | `-loop 1 -t -vf fade=in` 当第 0 段 | 也要 normalize、也进 ds |
| 字幕卡 | PIL(msyhbd.ttc 居中) → `-loop 1 -t fade in/out` | 中文必须显式给字体 |
| 缩略图 | `-map 0 -map 1:v -c copy -disposition:v:1 attached_pic` | 流拷贝秒级 |
| 掐头补救 | `-ss <t>` 在 `-i` 前 | 切完重探时长 |
| 尾段续拍 | 末帧→singleImage2video 续 4s→`xfade 0.3` 缝 | 前段一帧不改 |
| 中文路径 | PIL 原生 OK；cv2 用 `imdecode/imencode` | ffmpeg 用 list 形式 subprocess |
| 拼装自检 | 段数 + 序号连续 + 总时长 | 手写序列易漏镜/重复镜 |
