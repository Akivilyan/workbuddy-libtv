# -*- coding: utf-8 -*-
"""把阿里云帮助中心的页面（正文 SSR 在 script 字符串里）转成 markdown"""
import io, re, sys
from html.parser import HTMLParser


def unescape_aliyun(raw: str) -> str:
    """正文被塞在 script 的 JSON 字符串里，属性引号等被转义"""
    t = raw
    t = t.replace('\\"', '"')
    t = t.replace("\\'", "'")
    t = t.replace('\\n', '\n')
    t = t.replace('\\t', ' ')
    t = t.replace('\\/', '/')
    t = t.replace('\\u003c', '<').replace('\\u003e', '>')
    t = t.replace('\\\\', '\\')
    # 把 script 外壳去掉，让正文暴露出来
    t = re.sub(r'</?script[^>]*>', '\n', t)
    t = re.sub(r'</?style[^>]*>', '\n', t)
    return t


class MD(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.buf = []
        self.cell = []
        self.rows = []
        self.in_cell = False
        self.in_pre = False
        self.h = 0
        self.depth_skip = 0

    def _flush_to(self, s):
        txt = ''.join(self.buf).strip()
        txt = re.sub(r'[ \t]+', ' ', txt)
        txt = re.sub(r'\n{2,}', '\n', txt)
        self.buf = []
        return txt

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.depth_skip += 1
            return
        if self.depth_skip:
            return
        if tag == 'table':
            self.rows = []
        elif tag == 'tr':
            self.cell = []
        elif tag in ('td', 'th'):
            self.in_cell = True
            self.buf = []
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.h = int(tag[1])
            self.buf = []
        elif tag in ('p', 'li'):
            if not self.in_cell:
                self.buf = []
        elif tag == 'pre':
            self.in_pre = True
            self.buf = []
        elif tag == 'br':
            self.buf.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.depth_skip = max(0, self.depth_skip - 1)
            return
        if self.depth_skip:
            return
        BLOCK = ('table', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'pre')
        if tag not in BLOCK:
            # span / code / strong / a 等行内标签：保留已累积的文本，不清空
            return
        if self.in_cell and tag in ('p', 'li'):
            # 单元格内部的段落：内容留在 buf，等 td 结束统一取
            self.buf.append(' ')
            return
        txt = self._flush_to(self.buf)
        if tag == 'table':
            if self.rows:
                self.out.append(self.render_table(self.rows))
            self.rows = []
        elif tag == 'tr':
            if self.cell:
                self.rows.append(self.cell)
            self.cell = []
        elif tag in ('td', 'th'):
            self.cell.append(txt.replace('\n', ' ').strip())
            self.in_cell = False
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            if txt:
                self.out.append('#' * min(self.h, 6) + ' ' + txt)
        elif tag == 'p':
            if txt:
                self.out.append(txt)
        elif tag == 'li':
            if txt:
                self.out.append('- ' + txt)
        elif tag == 'pre':
            if txt:
                self.out.append('```\n' + txt + '\n```')
            self.in_pre = False

    def handle_data(self, data):
        if self.depth_skip:
            return
        self.buf.append(data)

    @staticmethod
    def render_table(rows):
        if not rows:
            return ''
        w = max(len(r) for r in rows)
        rows = [r + [''] * (w - len(r)) for r in rows]
        head = '| ' + ' | '.join(c.replace('|', '\\|') for c in rows[0]) + ' |'
        sep = '|' + '|'.join(['---'] * w) + '|'
        body = ['| ' + ' | '.join(c.replace('|', '\\|') for c in r) + ' |' for r in rows[1:]]
        return '\n'.join([head, sep] + body)


def cleanup(md: str) -> str:
    lines = md.split('\n')
    # 正文在页面里出现两遍（后一遍才带 h1 标题）：从最后一个一级标题起算
    titles = [i for i, l in enumerate(lines) if l.startswith('# ')]
    if titles:
        lines = lines[titles[-1]:]
    # 裁掉站点页脚
    FOOT = ('### 为什么选择阿里云', '### 关注阿里云', '### 友情链接')
    for i, l in enumerate(lines):
        if l.strip() in FOOT:
            lines = lines[:i]
            break
    md = '\n'.join(lines).rstrip()
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md


def convert(path, out_path):
    raw = io.open(path, encoding='utf-8', errors='ignore').read()
    t = unescape_aliyun(raw)
    p = MD()
    p.feed(t)
    # 去重相邻重复块（同一段可能被解析两遍）
    blocks = []
    for b in p.out:
        if not blocks or blocks[-1] != b:
            blocks.append(b)
    md = '\n\n'.join(blocks)
    md = cleanup(md)
    io.open(out_path, 'w', encoding='utf-8', newline='\n').write(md)
    return len(md), len(blocks)


if __name__ == '__main__':
    base = r'C:/Users/DCZX2/WorkBuddy/libtv/参考文档/raw/'
    out = r'C:/Users/DCZX2/WorkBuddy/libtv/参考文档/'
    for src, dst in [('wan3-guide.html', '阿里云官方-万相3.0视频生成.md'),
                     ('prompt-guide.html', '阿里云官方-万相提示词指南.md')]:
        n, b = convert(base + src, out + dst)
        print('%s -> %s : %d chars, %d blocks' % (src, dst, n, b))
