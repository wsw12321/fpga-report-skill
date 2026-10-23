r"""交付前检查实验报告 Markdown。

用法：
    python -I check_report.py <report.md> [--final]

检查项：
  1. 所有 ![...](路径) 引用的图片是否存在（相对 report.md 所在目录）；
  2. 是否残留占位标记（【待补】、TODO、TBD、XXX）—— 加 --final 时视为错误，否则只提示；
  3. 是否残留模板内容：模板作者的姓名学号、“Lab X”、模板中以“> 1. 请”开头的引导语；
  4. 模板要求的 6 个二级标题是否都在；
  5. 粗略统计 mermaid 图、代码块、图片和表格的数量，便于和上一次报告对比篇幅。
退出码：有错误时为 1。
"""
import re
import sys
from pathlib import Path

SECTIONS = ["实验目的与内容", "逻辑设计", "仿真结果与分析", "电路设计与分析", "测试结果与分析", "总结"]
TEMPLATE_RESIDUE = ["PB20111623", "马子睿", "# Lab X", "> 1. 请", "> 2. 请", "> 3. 请"]
PLACEHOLDERS = ["【待补", "TODO", "TBD", "XXX"]


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # python -I 会忽略 PYTHONIOENCODING
    if not argv:
        sys.exit(__doc__)
    path = Path(argv[0])
    final = "--final" in argv
    text = path.read_text(encoding="utf-8")
    errors, notes = [], []

    for m in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)\)", text):
        ref = m.group(1)
        if not re.match(r"https?://", ref) and not (path.parent / ref).exists():
            errors.append(f"missing image: {ref}")

    for i, line in enumerate(text.splitlines(), 1):
        for p in PLACEHOLDERS:
            if p in line:
                (errors if final else notes).append(f"placeholder '{p}' at line {i}: {line.strip()[:80]}")
        for r in TEMPLATE_RESIDUE:
            if r in line:
                errors.append(f"template residue '{r}' at line {i}: {line.strip()[:80]}")

    heads = re.findall(r"^## (.+)$", text, re.M)
    for s in SECTIONS:
        if not any(h.strip().startswith(s) for h in heads):
            errors.append(f"missing section: ## {s}")

    stats = {
        "mermaid": len(re.findall(r"^```mermaid", text, re.M)),
        "code blocks": len(re.findall(r"^```", text, re.M)) // 2,
        "images": len(re.findall(r"!\[", text)),
        "table rows": len(re.findall(r"^\|", text, re.M)),
        "lines": text.count("\n") + 1,
    }
    print("stats:", ", ".join(f"{k} {v}" for k, v in stats.items()))
    for n in notes:
        print("NOTE ", n)
    for e in errors:
        print("ERROR", e)
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
