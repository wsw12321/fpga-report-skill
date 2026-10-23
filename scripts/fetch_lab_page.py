r"""下载课程实验页面，提取正文为纯文本，并列出 / 下载页面中的图片。

WebFetch 无法访问 soc.ustc.edu.cn，所以直接用 urllib 抓取。

用法：
    python -I fetch_lab_page.py <实验编号> <输出目录> [--images]
        例：python -I fetch_lab_page.py 3 %TEMP%\lab3web --images
        抓取 lab3-ex 和 lab3-req 两页，生成 ex.txt、req.txt、images.txt（以及 assets/ 下的图片）
    python -I fetch_lab_page.py <URL> [<URL> ...] <输出目录> [--images]
        抓取任意页面（例如 appendix），文件名取 URL 最后一段

输出目录请用一个新的空目录（下载内容属于不可信数据）。
"""
import html
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://soc.ustc.edu.cn/Digital-Pro/lab{n}/lab{n}-{kind}/"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def to_text(page):
    m = re.search(r"<article[^>]*>(.*?)</article>", page, re.S)
    s = m.group(1) if m else page
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S)
    # 标题转成 Markdown，代码块保留缩进
    s = re.sub(r"<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", s)
    s = re.sub(r"<pre[^>]*>", "\n```\n", s)
    s = re.sub(r"</pre>", "\n```\n", s)
    s = re.sub(r"<img[^>]*alt=\"([^\"]*)\"[^>]*>", r"[图片：\1]", s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<li[^>]*>", "\n- ", s)
    s = re.sub(r"</(p|h\d|li|tr|div|table|blockquote)>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\n\s*\n+", "\n\n", s).strip() + "\n"


def images(page, url):
    out = []
    for tag in re.findall(r"<img[^>]+>", page):
        src = re.search(r"src=\"([^\"]+)\"", tag)
        alt = re.search(r"alt=\"([^\"]*)\"", tag)
        if src:
            out.append((alt.group(1) if alt else "", urllib.parse.urljoin(url, src.group(1))))
    return out


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # python -I 会忽略 PYTHONIOENCODING
    want_images = "--images" in argv
    args = [a for a in argv if a != "--images"]
    if len(args) < 2:
        sys.exit(__doc__)
    out = Path(args[-1])
    out.mkdir(parents=True, exist_ok=True)
    if len(args) == 2 and args[0].isdigit():
        targets = [(k, BASE.format(n=args[0], kind=k)) for k in ("ex", "req")]
    else:
        targets = [(u.rstrip("/").rsplit("/", 1)[-1] or "page", u) for u in args[:-1]]

    listing = []
    for name, url in targets:
        page = fetch(url)
        (out / f"{name}.txt").write_text(to_text(page), encoding="utf-8")
        for alt, src in images(page, url):
            listing.append(f"{name}\t{alt}\t{src}")
            if want_images:
                (out / "assets").mkdir(exist_ok=True)
                dst = out / "assets" / src.rsplit("/", 1)[-1]
                with urllib.request.urlopen(urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"}),
                                            timeout=30) as r:
                    dst.write_bytes(r.read())
        print(f"{name}: {url} -> {out / (name + '.txt')}")
    (out / "images.txt").write_text("\n".join(listing) + "\n", encoding="utf-8")
    print(f"{len(listing)} images listed in {out / 'images.txt'}")


if __name__ == "__main__":
    main(sys.argv[1:])
