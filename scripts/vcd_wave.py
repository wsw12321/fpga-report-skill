r"""把 xsim 导出的 VCD 画成报告用的波形图（需要 matplotlib）。

两种用法：

1. 命令行快速出图：
   python -I vcd_wave.py <vcd> <out.png> --signals clk,dut.cnt:dec,an:bin,seg:seg [--t0 0] [--t1 2000]
          [--unit ns|cycles|<每单位多少 ns>] [--clk-ns 10] [--title "..."] [--subtitle "..."]
   - 信号名是去掉顶层模块名后的层次名（例如 dut.timer_inst.q）；
   - 格式后缀：bit（1 位电平）、dec、hex、bin、seg（低有效 {a..g} 段码 → 数字），默认 1 位为 bit、多位为 hex；
   - --t0 / --t1 以 ns 为单位；--unit cycles 时横轴为时钟周期数（需要 --clk-ns）。

2. 在各次实验自己的绘图脚本中导入：
   import sys; sys.path.insert(0, r"<skill>/scripts")
   from vcd_wave import Wave, draw, figure, save, dec, hx, bn, seg7
   w = Wave("tb.vcd")
   t0 = w.first("dut.cnt", lambda v: v == 12345)            # 按信号取值找时间窗口
   fig, axes = figure(5.4, [1], "标题", "副标题", top_in=1.0)
   draw(axes[0], w, [("clk", "clk", "bit", GREY), ("dut.cnt", "cnt", dec, GREEN)],
        t0, t0 + 900, scale=10, xlabel="时钟周期", grid=100)
   save(fig, "pic/Lab-N-sim-xxx.png")

注意：Wave.first() 会从时间 0 开始找，如果信号的初值恰好满足条件，会匹配到 t = 0。
需要“某次测试之后的第一次”时，先找到该测试的起点，再用 after= 参数。
"""
import argparse
import re
import sys
from bisect import bisect_right
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

BLUE, GREEN, PURPLE, ORANGE, GREY = "#3977bb", "#089981", "#9270b6", "#d9822b", "#52627a"
FONT = ["1111110", "0110000", "1101101", "1111001", "0110011",
        "1011011", "1011111", "1110000", "1111111", "1111011"]
SEG2DIGIT = {int(f, 2) ^ 0x7F: d for d, f in enumerate(FONT)}   # 低有效 {a,b,c,d,e,f,g}

plt.rcParams.update({"font.family": ["Microsoft YaHei", "DejaVu Sans"],
                     "font.size": 10, "axes.unicode_minus": False})


def to_int(v):
    return None if re.search("[xzXZ]", v) else int(v, 2)


dec = lambda v: str(v)
hx = lambda w: (lambda v: f"{v:0{(w + 3) // 4}X}")
bn = lambda w: (lambda v: f"{v:0{w}b}")
seg7 = lambda v: f"{v:07b}→{SEG2DIGIT.get(v, '?')}"


def load_vcd(path):
    """返回 ({信号全名: [(时间 ns, 值字符串), ...]}, {信号全名: 位宽})，全名不含顶层模块名。"""
    text = Path(path).read_text()
    unit = re.search(r"\$timescale\s+(\d+)\s*(\w+)\s+\$end", text)
    ns_per_tick = int(unit[1]) * {"s": 1e9, "ms": 1e6, "us": 1e3, "ns": 1, "ps": 1e-3, "fs": 1e-6}[unit[2]]
    head, body = text.split("$enddefinitions", 1)
    scopes, codes, traces, widths = [], {}, {}, {}
    for line in head.splitlines():
        tok = line.split()
        if tok[:1] == ["$scope"]:
            scopes.append(tok[2])
        elif tok[:1] == ["$upscope"]:
            scopes.pop()
        elif tok[:1] == ["$var"]:
            name = ".".join(scopes[1:] + [tok[4]])
            codes.setdefault(tok[3], []).append(name)
            traces[name], widths[name] = [], int(tok[2])
    t = 0.0
    for line in body.splitlines()[1:]:
        if not line:
            continue
        c = line[0]
        if c == "#":
            t = int(line[1:]) * ns_per_tick
        elif c in "br":
            value, code = line[1:].split()
            for n in codes.get(code, []):
                traces[n].append((t, value))
        elif c in "01xXzZ":
            for n in codes.get(line[1:], []):
                traces[n].append((t, c))
    return traces, widths


class Wave:
    def __init__(self, path):
        self.tr, self.width = load_vcd(path)
        self.times = {n: [p[0] for p in v] for n, v in self.tr.items()}
        self.end = max((v[-1][0] for v in self.tr.values() if v), default=0.0)

    def at(self, name, t):
        i = bisect_right(self.times[name], t) - 1
        return to_int(self.tr[name][i][1]) if i >= 0 else None

    def segments(self, name, t0, t1):
        """[(left, right, 值字符串)]；同一时刻的多次变化只保留最后一次，相同的值合并。"""
        changes = []
        for time, value in self.tr[name]:
            if changes and changes[-1][0] == time:
                changes[-1] = (time, value)
            elif not changes or changes[-1][1] != value:
                changes.append((time, value))
        out = []
        for i, (left, value) in enumerate(changes):
            right = changes[i + 1][0] if i + 1 < len(changes) else float("inf")
            if left < t1 and right > t0:
                out.append((max(left, t0), min(right, t1), value))
        return out

    def first(self, name, pred, after=0.0):
        for time, value in self.tr[name]:
            if time >= after and (v := to_int(value)) is not None and pred(v):
                return time
        raise ValueError(f"{name}: no match after {after}")


def draw(ax, wave, rows, t0, t1, scale=1.0, xlabel="", grid=None):
    """rows: [(信号名, 显示名, 格式, 颜色)]，格式为 'bit' 或把整数转成标签的函数。
    t0 / t1 / grid 以 ns 为单位，横轴刻度 = 时间 / scale。总线太窄放不下标签时不写标签。"""
    ax.set_facecolor("white")
    px_per_unit = ax.get_window_extent().width / ((t1 - t0) / scale)
    if grid:
        g = grid * (int(t0 / grid) + 1)
        while g < t1:
            ax.axvline(g / scale, color="#e3e9f1", lw=.7, zorder=0)
            g += grid
    for row, (name, label, fmt, color) in enumerate(rows):
        y = len(rows) - 1 - row
        for left, right, value in wave.segments(name, t0, t1):
            l, r = left / scale, right / scale
            if fmt == "bit":
                lvl = y + (.28 if value == "1" else -.28)
                ax.plot([l, r], [lvl, lvl], color=color, lw=1.6, solid_capstyle="butt")
                ax.plot([l, l], [y - .28, y + .28], color=color, lw=.8, alpha=.5)
                continue
            inset = min(.012 * (t1 - t0) / scale, (r - l) / 3)
            verts = [(l, y), (l + inset, y + .3), (r - inset, y + .3),
                     (r, y), (r - inset, y - .3), (l + inset, y - .3)]
            ax.add_patch(Polygon(verts, facecolor=color + "12", edgecolor=color, lw=1))
            iv = to_int(value)
            text = fmt(iv) if iv is not None else "X"
            if (r - l) * px_per_unit > 7.5 * len(text) + 6:
                ax.text((l + r) / 2, y, text, ha="center", va="center", fontsize=8.5,
                        fontfamily="DejaVu Sans Mono", color="#1e334d")
    ax.set(xlim=(t0 / scale, t1 / scale), ylim=(-.7, len(rows) - .3), xlabel=xlabel,
           yticks=range(len(rows) - 1, -1, -1), yticklabels=[r[1] for r in rows])
    ax.tick_params(axis="both", length=0, pad=6)
    for spine in ax.spines.values():
        spine.set_visible(False)


def figure(h, ratios, title, subtitle, top_in=1.0, hspace=.55, w=16):
    """h：图高（英寸）；ratios：各面板高度比；top_in：标题区高度（英寸）。
    标题和副标题都用 va='top' 按英寸定位，避免两者重叠；有面板标题时 top_in 取 1.2 左右。"""
    fig, axes = plt.subplots(len(ratios), 1, figsize=(w, h), gridspec_kw={"height_ratios": ratios})
    axes = list(axes) if len(ratios) > 1 else [axes]
    fig.patch.set_facecolor("#f4f7fb")
    fig.text(.06, 1 - .15 / h, title, fontsize=18, va="top")
    fig.text(.06, 1 - .62 / h, subtitle, color=GREY, fontsize=10.5, va="top")
    fig.subplots_adjust(left=.1, right=.985, top=1 - top_in / h, bottom=.8 / h, hspace=hspace)
    fig.canvas.draw()      # 先布局，draw() 才能按像素判断标签放不放得下
    return fig, axes


def save(fig, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(path)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # python -I 会忽略 PYTHONIOENCODING
    p = argparse.ArgumentParser(description="quick VCD plot")
    p.add_argument("vcd")
    p.add_argument("out")
    p.add_argument("--signals", required=True, help="name[:bit|dec|hex|bin|seg],...")
    p.add_argument("--t0", type=float, default=0.0)
    p.add_argument("--t1", type=float, default=None)
    p.add_argument("--unit", default="ns", help="ns | cycles | 每个横轴单位对应的 ns 数")
    p.add_argument("--clk-ns", type=float, default=10.0)
    p.add_argument("--title", default="")
    p.add_argument("--subtitle", default="")
    a = p.parse_args()

    w = Wave(a.vcd)
    t1 = a.t1 if a.t1 is not None else w.end
    scale = {"ns": 1.0, "cycles": a.clk_ns}.get(a.unit) or float(a.unit)
    xlabel = {"ns": "时间 / ns", "cycles": "时钟周期"}.get(a.unit, f"时间 / ({a.unit} ns)")
    palette = [BLUE, GREEN, PURPLE, ORANGE]
    rows = []
    for i, spec in enumerate(a.signals.split(",")):
        name, _, f = spec.partition(":")
        if name not in w.tr:
            raise SystemExit(f"unknown signal {name}; available: {', '.join(sorted(w.tr))}")
        width = w.width[name]
        f = f or ("bit" if width == 1 else "hex")
        fmt = {"bit": "bit", "dec": dec, "hex": hx(width), "bin": bn(width), "seg": seg7}[f]
        rows.append((name, name, fmt, GREY if name.endswith("clk") else palette[i % 4]))
    fig, axes = figure(1.2 + .55 * len(rows), [1], a.title or Path(a.vcd).name, a.subtitle, top_in=1.0)
    draw(axes[0], w, rows, a.t0, t1, scale=scale, xlabel=xlabel)
    save(fig, a.out)


if __name__ == "__main__":
    main()
