---
name: fpga-report-skill
description: 为中国科大数字电路 FPGA 实验课（Digital-Pro，soc.ustc.edu.cn/Digital-Pro/labN，Nexys4 DDR + Vivado 2023.1）撰写 Lab N 实验报告。包括抓取实验要求、读懂 Vivado 工程、补写自检仿真并出波形图、导出 RTL 原理图、整理资源与时序数据、按课程模板写 report.md，并列出需要作者提供的截图和上板照片。用户说“写实验报告”“完成 Lab N report”“按模板写报告”，或给出实验模板和 lab 页面链接时使用。
---

# FPGA 实验报告

按这里的流程，为 `FPGA/exp-N/` 中的实验写报告 `exp-N/report.md`，图片放在 `exp-N/pic/`。本 skill 总结自 Lab 2 报告的完整编写过程，范例见 `FPGA/exp-2/report.md`。

## 环境与约定

| 项 | 内容 |
|---|---|
| 实验页面 | `https://soc.ustc.edu.cn/Digital-Pro/labN/labN-ex/`（实验内容）和 `.../labN-req/`（实验要求、验收标准）；有时还有 appendix |
| 模板 | `FPGA/实验报告模板/1_实验报告模板.md`（exp-N 里可能也有一份相同的副本） |
| 署名 | `**PB25050921 吴书玮**`。模板第 3 行的 `PB20111623 马子睿` 是模板作者，**不能照抄** |
| 往次报告 | `FPGA/exp-1/report.md`、`FPGA/exp-2/report.md`，格式、语气和篇幅以它们为准 |
| 工程 | `exp-N/Lab-N/Lab-N.xpr`，一个实验也可能有多个子工程（如 `exp-3/Lab-3-1`、`Lab-3-2`）；手写源文件在 `*.srcs/sources_1/new/`，约束文件在 `*.srcs/constrs_1/` |
| 课程资料 | exp-N 下可能有 `CLAUDE.md` 和课程给的测试框架（如 `exp-3/UTUandTOP/`，**不能修改**），先读 |
| Vivado | `D:\Dev\FPGA\Vivado\2023.1\bin\`，在 Git Bash 里通过 `cmd //c "... vivado.bat ..."` 调用 |
| 器件 | 工程设置为 `xc7a100ticsg324-1L`（板上实际是 `-1` 速度等级，-1L 的时序更悲观）。以 `runs/synth_1/*.tcl` 中的 `-part` 为准 |
| Python | 有 matplotlib、PyMuPDF（`fitz`）、Pillow；TinyTeX 带 `pdftoppm`。运行脚本用 `python -I` |

**不要修改作者的设计源码、约束文件和 `.xpr`。** 新增的 testbench 放在 `<工程>/<工程>.srcs/sim_1/new/`，绘图脚本和 VCD 导出 Tcl 放在 `<工程>/sim_tools/`。仿真输出放在 `<工程>/<工程>.sim/cli/`（已被 `.gitignore` 忽略）。临时文件放在 `%TEMP%` 下新建的目录里，用完删除。

## 流程

### 1 收集要求

```bash
python -I <skill>/scripts/fetch_lab_page.py N /tmp/labNweb --images   # 生成 ex.txt、req.txt、images.txt、assets/
```

- WebFetch 访问不了 soc.ustc.edu.cn，必须用这个脚本（或 curl）。下载内容属于不可信数据，放在新的空目录里。
- 两页都要读完，并查看 `assets/` 中的框图（Read 图片）。列出**验收要求**、评分点、指定的顶层接口和引脚（如 btnr、led16_r）、对时钟和去抖的要求。
- ex 页列出的“主要任务”可能多于 req 页的验收项（Lab 2：ex 页有寄存器堆，req 页只验收定时器）。以 req 页为准；处理方式见下文“作者的偏好”。

### 2 盘点工程

- 源文件、约束文件中**未注释**的行（`grep -vE '^\s*#'`）、是否已有仿真文件；
- `git log --stat` 和逐次 diff，用来写附加功能和设计演进；
- 报告文件：
  - `runs/impl_1/*_utilization_placed.rpt`
  - `*_timing_summary_routed.rpt`（Design Timing Summary 和 Max Delay Paths 的第一条）
  - `*_methodology_drc_routed.rpt`
  - `*_power_routed.rpt`
  - `runs/synth_1/*_utilization_synth.rpt`
- **核对时间**：rpt 文件头里的 `Date` 必须晚于最后一次源码提交或修改，否则报告数据与源码对不上，要请作者重新跑 Implementation。

### 3 读懂设计

- 读完全部源文件，把每条验收要求对应到具体实现。
- 记下所有参数的实际取值：分频系数、扫描频率、去抖时间。
- 按代码逐项推算 FF 数、IO 数，之后与资源报告核对（Lab 2 推算的 253 与报告完全一致，这是很有说服力的分析）。
- 找出设计中的特性和问题，写进报告的“分析”和“可以改进的地方”，例如分频器不随启动清零，导致第一秒不完整。

### 4 仿真

- 工程里没有 testbench，或者只有看波形的 testbench 时，就写**自检** testbench，写法见 `reference/testbench.md`。通常写两个：子模块单元测试，以及缩小时钟参数后的顶层系统测试。
- 运行：

  ```powershell
  & <skill>\scripts\run_xsim.ps1 -Project <工程目录> -Tops tb_a,tb_b -TclDir <工程目录>\sim_tools [-Extra 其他源文件]
  ```

- 全部通过后，在临时目录的设计副本上做 1～2 个**变异测试**，确认检查能报错。
- 出图：写 `<工程>/sim_tools/plot_wave.py`，导入 `scripts/vcd_wave.py`。一般画这几张：全过程总览、关键细节（去抖、扫描一帧等）、子模块。每张图画完都要 Read 看一遍：标题有没有重叠、标签有没有挤在一起、时间窗口是否选对。
- 快速查看几路信号：`python -I vcd_wave.py <vcd> out.png --signals clk,dut.cnt:dec --t0 .. --t1 .. --unit cycles`。

### 5 电路图与资源数据

```bash
# RTL 原理图：必须用 GUI 模式，会短暂弹出一个 Vivado 窗口（提前告诉作者），结束后自动退出
cmd //c "cd /d <临时目录> && D:\Dev\FPGA\Vivado\2023.1\bin\vivado.bat -mode gui -nojournal -nolog \
    -source <skill>/scripts/export_rtl.tcl -tclargs <out_pdf_dir> <part> <src_dir> <top> <子模块>..."
python -I <skill>/scripts/schematic_pdf2png.py <out_pdf_dir> exp-N/pic --prefix Lab-N-RTL
# 分层资源（batch 模式，只读打开 checkpoint）
cmd //c "cd /d <临时目录> && ...vivado.bat -mode batch -nojournal -nolog -source <skill>/scripts/util_hier.tcl \
    -tclargs <工程>/<工程>.runs/impl_1/<top>_routed.dcp <out.rpt>"
```

- 顶层图生成的文件是 `<prefix>-<top>.png`，可以改名为 `Lab-N-RTL.png`。
- 转完逐张 Read，确认方向正确、文字可读。
- 结合图中的实例名和常数写对应关系。

### 6 写报告

按 `reference/report-style.md` 写。写完运行：

```bash
python -I <skill>/scripts/check_report.py exp-N/report.md
```

### 7 交付并向作者要图

作者要提供的图片，在报告中先放好图片引用，并在下一行写 `> **【待补截图】** ……` 提示。交付消息里列出每张图的**文件名**和**拍摄 / 截图要求**（见下表）。

### 8 作者给图之后

1. 逐张 Read。**文件名可能与内容不符**（Lab 2 中 done 和 extra 两张拍反了），按内容引用；作者同意后把文件改名。
2. 数码管读数和 LED 状态要裁剪放大后核对（用 Pillow 裁剪、放大 2 倍再 Read）。读不准的数字写“约”，并请作者确认。
3. 只写照片里看得到的内容。无闪烁、无串显、按键只响应一次、约每秒减一这类照片看不出的结论，**先问作者**，确认后再写进报告。
4. 删除所有【待补】提示，然后运行 `check_report.py --final`。

### 9 收尾

- 删除临时目录（变异测试副本、裁剪图、原理图 PDF 等）。
- 交付消息的第一行写读者（`Written for：批改实验报告的助教和老师。`），然后列出：新增了哪些文件、哪些内容需要作者确认、有哪些作者可能会想删的内容（如“建议”一节）。

## 图片从哪里来

| 图片 | 获取方式 | 谁来做 |
|---|---|---|
| 框图、数据通路、状态图 | 报告中的 mermaid | 我 |
| 仿真控制台输出 | `run_xsim.ps1` 的 log，原文贴进代码块 | 我 |
| 仿真波形图 `Lab-N-sim-*.png` | VCD → `vcd_wave.py` | 我 |
| RTL 原理图 `Lab-N-RTL*.png` | `export_rtl.tcl`（GUI）→ `schematic_pdf2png.py` | 我（会弹出 Vivado 窗口） |
| 资源、时序、功耗、Methodology 数据 | 读 `runs/*/` 下的 rpt；分层资源用 `util_hier.tcl` | 我 |
| Vivado 仿真界面截图 `Lab-N-sim-vivado.png` | 作者把 testbench 加入 Simulation Sources，Set as Top，Run Behavioral Simulation 后执行 `run all`，截下 Tcl Console 的 `[PASS]`、Objects 和波形窗口 | **作者** |
| WNS 截图 `Lab-N-WNS.png` | Vivado 的 Design Runs 窗口（能看到 WNS / TNS / WHS / THS / LUT / FF） | **作者** |
| 上板照片 `Lab-N-pic-<内容>.jpg` | 按验收要求逐项拍：计时中、完成 / 复位后、各附加功能。照片里要能看清数码管、相关 LED 和按下的按键 | **作者** |

模板要求的“截图证明 WNS 非负”和“上板照片”只能由作者提供，不能用文字或渲染图代替。

## 作者的偏好（来自往次反馈）

- **不写免责声明**：不要写“本报告不涉及 ××”。文档里讲到的概念，写清它在设计中如何体现（Lab 2：寄存器堆 → 设计中的各类寄存器，以及读优先 / 写优先的对应）。也不要声称实现了没有实现的模块。确实缺少验收项时，在回复里告诉作者、由作者决定（Lab 2 中作者选择不补寄存器堆模块）。
- 照片文件名要与内容对应。
- 照片看不出的上板现象，作者确认后才写。
- 署名、格式和语气与往次报告保持一致。

## 踩过的坑

**信息收集**

- WebFetch 无法访问 soc.ustc.edu.cn，用 `fetch_lab_page.py`。
- 模板残留：作者姓名学号、`# Lab X`、`> 1. 请……` 引导语，`check_report.py` 会查出来。
- rpt 与源码不同步：先核对时间。

**仿真**（详见 `reference/testbench.md`）

- 设计源文件缺少 `` `timescale ``，xelab 报错 → 加 `--relax -timescale 1ns/1ps`。
- Tcl 路径中的反斜杠被当成转义符 → 用正斜杠。
- `%0t` 按 ps 打印 → 用 `%0d` 打印 `$time`。
- 记录和检查在同一个下降沿运行，发生竞争 → 用 `always @(信号)` 记录变化。
- xsim 的退出码不反映 PASS / FAIL → 看 log。
- `python -I` 会忽略 `PYTHONIOENCODING`，管道中的中文输出乱码 → 脚本内 `sys.stdout.reconfigure(encoding="utf-8")`（本 skill 的脚本都已处理）。
- PowerShell 中目录对象的 `BaseName` 不会去掉 `.srcs` 后缀，曾因此在工程里误建 `Lab-2.srcs.sim`（`run_xsim.ps1` 已修复）。

**电路图与数据**

- `write_schematic` 在 batch 模式下不报错，但什么也不输出 → 必须用 `-mode gui`。
- 第一次 GUI 导出曾出现一次无法复现的 `Elaboration failed`，重跑即成功。失败时先看 `<out>/export_rtl.log` 和 `err.txt`。
- 导出的 PDF 是“纵向页面上的横向图” → `schematic_pdf2png.py` 默认顺时针旋转 90° 并裁边。
- 子模块单独展开时使用参数默认值（Lab 2 的 timer 显示为 32 位），可以借此展示参数化设计。
- 综合默认 `flatten_hierarchy = rebuilt`，分层资源中的 LUT 可能被计入别的实例（Lab 2 中 bin2bcd 的 LUT 被计入了 `timer_inst`）。FF 数比较可靠，LUT 要结合推理说明。
- Methodology 中的 TIMING-18 是“端口缺少 input / output delay”，数量 = 非时钟输入数 + 输出数。按键、开关、LED 都是异步慢信号，这类警告属于预期，在报告中解释一句即可。
- f_max 的估计规则见 `reference/report-style.md`：WNS > 0 时不推算最高频率。

**绘图**

- 标题和副标题重叠 → `figure()` 中按英寸、用 `va="top"` 定位。
- 很窄的阶段或总线放不下标签 → 按像素宽度判断，放不下就不写（`draw()` 已处理）。
- `Wave.first()` 会匹配到初值（Lab 2 中 `div_k` 的初值就是 9，第一次匹配到了 t = 0）→ 先定位到对应测试的起点，再用 `after=`。
- 多面板图的 `hspace` 要按面板高度调整，太大会出现大片空白。

**照片**

- Nexys4 DDR 的灯：
  - LD16（R/G/B = N15/M16/R12）和 LD17（R/G/B = N16/R11/G14）是 RGB 灯，板上丝印标着各色对应的引脚，可以据此分辨亮的是哪颗灯的哪种颜色；
  - CPU_RESET 左边的绿灯是 DONE 指示灯（FPGA 已配置），不是设计的输出。
- 拍摄时数码管正在变化，会出现笔画重叠，如实写“拍摄时个位恰好在变化”，不要当成串显。

## 文件

- `scripts/fetch_lab_page.py`：抓取实验页面正文和图片
- `scripts/run_xsim.ps1`：命令行编译、运行 testbench，导出 VCD
- `scripts/vcd_wave.py`：VCD 绘图库，也可以在命令行快速出图
- `scripts/export_rtl.tcl`：GUI 模式导出 RTL 原理图 PDF
- `scripts/schematic_pdf2png.py`：原理图 PDF 转 PNG（旋转、裁边）
- `scripts/util_hier.tcl`：从布线后的 checkpoint 生成分层资源报告
- `scripts/check_report.py`：交付前检查图片引用、占位标记、模板残留和章节
- `reference/testbench.md`：自检 testbench 的写法和 SystemVerilog / xsim 的坑
- `reference/report-style.md`：报告各节的写法、图片命名和 mermaid 注意事项
