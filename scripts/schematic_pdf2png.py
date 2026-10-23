r"""把 export_rtl.tcl 导出的原理图 PDF 转成适合放进报告的 PNG：旋转成横向、裁掉白边、限制宽度。

用法：
    python -I schematic_pdf2png.py <pdf_dir> <out_dir> [--prefix Lab-N-RTL] [--rotate -90] [--width 3600]
        对 <pdf_dir> 中的每个 <top>.pdf 生成 <out_dir>/<prefix>-<top>.png
        --rotate：PIL 的逆时针角度，Vivado 横向导出时用默认的 -90（顺时针 90°，输入端口在左、输出端口在右）

依赖 PyMuPDF（import fitz）和 Pillow。没有 PyMuPDF 时可以先用 TinyTeX 自带的 pdftoppm 转成 PNG，再用 Pillow 旋转裁边。
转完务必打开图片看一眼：确认方向正确、文字清晰，再写进报告。
"""
import argparse
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageOps


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # python -I 会忽略 PYTHONIOENCODING
    p = argparse.ArgumentParser()
    p.add_argument("pdf_dir")
    p.add_argument("out_dir")
    p.add_argument("--prefix", default="RTL")
    p.add_argument("--rotate", type=int, default=-90)
    p.add_argument("--width", type=int, default=3600)
    a = p.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for pdf in sorted(Path(a.pdf_dir).glob("*.pdf")):
        page = fitz.open(pdf)[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(6, 6), alpha=False)     # 约 430 dpi，缩小后仍然清晰
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        if a.rotate:
            im = im.rotate(a.rotate, expand=True)
        box = ImageOps.invert(im.convert("L")).point(lambda v: 255 if v > 8 else 0).getbbox()
        im = im.crop((max(box[0] - 40, 0), max(box[1] - 40, 0),
                      min(box[2] + 40, im.width), min(box[3] + 40, im.height)))
        if im.width > a.width:
            im = im.resize((a.width, round(im.height * a.width / im.width)), Image.LANCZOS)
        dst = out / f"{a.prefix}-{pdf.stem}.png"
        im.save(dst, optimize=True)
        print(dst, im.size)


if __name__ == "__main__":
    main()
