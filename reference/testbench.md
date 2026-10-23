# 自检 testbench 的写法

完整的可运行例子：`FPGA/exp-2/Lab-2/Lab-2.srcs/sim_1/new/tb_units.sv`（子模块单元测试）和 `tb_lab_2.sv`（顶层系统测试），配套的 VCD 导出 Tcl 和绘图脚本在 `FPGA/exp-2/Lab-2/sim_tools/`。

## 总体原则

- **自检，不靠肉眼看波形**：每一项检查都计数，出错时打印时间和原因，最后打印 `[SUMMARY] checks = N, errors = M` 和 `[PASS]` / `[FAIL]`，再 `$finish`。报告里直接贴这些输出。
- **参考模型独立于设计**：不要照抄设计里的常数或写法。例如七段码按 a～g **高有效**写字形表，比较时再取反；乘法器的参考值用 testbench 里的 `$signed(a) * $signed(b)`（只有设计不许用 `*`）；定时器的参考模型按实验文档的文字描述单独写。
- **只改参数，不改设计**：如果设计把时钟频率做成了参数（如 `CLK_FREQ`），系统测试就把它缩小（Lab 2 用 10000，仿真中“1 秒” = 10000 拍），所有时间常数按比例缩小，而且可以**逐拍精确**地检查间隔（必须恰好等于 `CLK_FREQ` 拍）。如果设计里把常数写死了，就在子模块层面单独测试，不要去改设计源码。
- **激励尽量加在端口上**，显示结果尽量从端口还原（`an` / `seg` → 数字）；测量时间间隔这类需要内部信号的检查可以用层次引用（`dut.cnt`），在报告里说明。
- **测完再做变异测试**（见文末），证明检查真的能发现错误。

## 常用片段

```systemverilog
int checks = 0, errors = 0;
// 写成 void function 而不是 task：function 里不能调用 task，而很多检查要在 function 里做
function automatic void check(input bit ok, input string msg);
    checks++;
    if (!ok) begin
        errors++;
        if (errors <= 20) $display("[FAIL] %0d ns  %s", $time, msg);   // 不要用 %0t，它默认按 ps 打印
    end
endfunction
```

热路径（每拍都跑的监视器）里先判断再格式化，避免每拍都 `$sformatf`：

```systemverilog
if (cond) checks++;
else check(0, $sformatf("..."));
```

**七段码还原**：

```systemverilog
localparam logic [6:0] FONT [10] = '{   // a~g 高有效
    7'b1111110, 7'b0110000, 7'b1101101, 7'b1111001, 7'b0110011,
    7'b1011011, 7'b1011111, 7'b1110000, 7'b1111111, 7'b1111011 };
function automatic int seg2digit(input logic [6:0] s);
    for (int i = 0; i < 10; i++) if (s === ~FONT[i]) return i;
    return -1;
endfunction
```

**每拍监视器**：检查不变量，例如 `an` 恰好一位为 0 且无 X（`!$isunknown(an) && $countones(~an) == 1`）、显示的数字等于计数值的对应十进制位、`td == (cnt == 0)`、每位点亮拍数和扫描顺序。

**机械按键抖动**（`ref` 参数要求 task 是 automatic）：

```systemverilog
task automatic bounce(ref logic b, input logic level);
    for (int i = 0; i < 4; i++) begin
        b = level;  repeat (DEB / 5 + 3 * i) @(negedge clk);   // 每次都短于去抖阈值
        b = ~level; repeat (DEB / 10) @(negedge clk);
    end
    b = level;
endtask
task automatic press(ref logic b, input int hold, input logic active = 1'b1);
    bounce(b, active);  repeat (hold) @(negedge clk);
    bounce(b, ~active); repeat (2 * DEB) @(negedge clk);
endtask
```

**记录信号变化的时刻**（用来精确检查间隔）：

```systemverilog
longint cyc = 0;
always @(posedge clk) cyc++;
typedef struct { longint t; int v; } event_t;
event_t cnt_log [$];
// 在 cnt 变化的那一刻（上升沿的 NBA 区）就记录。不要在 negedge 上比较“当前值 != 上次值”再记录：
// 检查任务也在同一个 negedge 运行，两者竞争，检查时最后一条可能还没写进队列。
always @(dut.cnt) cnt_log.push_back('{cyc, int'(dut.cnt)});
```

**统计一次按键产生的内部上升沿**：在 negedge 采样 `dut.timer_inst.st_rise`，下一个 negedge 记录装载后的值，检查“一次按键恰好一个上升沿、装载值等于开关值”。

**随机对拍**：固定种子的 xorshift32，保证每次运行结果一样：

```systemverilog
function automatic logic [31:0] xorshift(input logic [31:0] x);
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    return x;
endfunction
```

## SystemVerilog / xsim 的坑

| 现象 | 原因 / 解决 |
|---|---|
| xelab 报 `XSIM 43-4099 ... doesn't have a timescale` | 设计源文件没有 `` `timescale ``；加 `--relax -timescale 1ns/1ps`（`run_xsim.ps1` 已处理）。Vivado 工程模式默认就带 `--relax` |
| `-tclbatch` 找不到脚本，路径里的反斜杠全没了 | Tcl 把 `\` 当转义符，路径改成正斜杠 |
| `[FAIL] 301020000 ns` 数值大了 1000 倍 | `%t` 默认按仿真精度（ps）打印；用 `%0d` 打印 `$time` |
| `foreach` 遍历 `localparam` 数组 | 并非所有工具都支持，直接用普通 `for` 循环更稳妥（Lab 2 中是预防性地这样写的，没有实际验证 xsim 是否支持） |
| 循环体里 `int x = v;` 只在第一次初始化 | 静态变量的初始化只做一次；在 automatic task 里也建议“先声明、再赋值” |
| 检查任务看不到刚发生的变化 | 同一时刻多个进程的竞争，见上面“记录信号变化的时刻” |
| xsim 退出码为 0，但测试其实失败了 | xsim 的退出码不反映 testbench 结果，看 log 里的 `[PASS]` / `[FAIL]` |
| `actual bit length 32 differs from formal bit length N` 警告 | 常数或表达式位宽大于端口位宽，只要值不溢出就无害；在报告里不必提 |

## 在 Vivado 工程中运行（给作者截图用）

1. Add Sources → Add or create simulation sources，加入 `sim_1/new/` 下的 testbench；
2. Simulation Sources 中右键 testbench → Set as Top；
3. Run Behavioral Simulation，然后在 Tcl Console 执行 `run all`（默认只跑 1000 ns）；
4. 截取 Tcl Console 的 `[PASS]` 输出、Objects 窗口和波形窗口。

## 导出 VCD 供绘图

每个 testbench 配一个同名 Tcl（放在 `<工程>/sim_tools/<top>.tcl`），只导出需要画的信号，避免 VCD 过大：

```tcl
open_vcd tb_lab_2.vcd
log_vcd [get_objects /tb_lab_2/clk /tb_lab_2/st /tb_lab_2/an /tb_lab_2/seg /tb_lab_2/td]
log_vcd [get_objects /tb_lab_2/dut/cnt /tb_lab_2/dut/st_s /tb_lab_2/dut/display_inst/sel]
run all
close_vcd
quit
```

xelab 需要 `-debug typical` 才能导出内部信号（`run_xsim.ps1` 已加）。在 testbench 里放一个 `int test_id`，每个测试开始时赋值，绘图时可以用它标出各测试阶段。

## 变异测试

在**临时目录的设计副本**上做，不碰原工程：

1. 复制 `sources_1/new/*` 和 testbench 到临时目录；
2. 用 `sed` 做一处有代表性的错误修改，例如去掉 `q != 0` 条件（减到 0 后回绕）、颠倒显示位序 `bcd[sel]` → `bcd[4 - sel]`、把 `<=` 改成 `<`；
3. 在临时目录编译运行，确认 testbench 报 `[FAIL]`，并记下首条错误信息；
4. 在报告的“分析”中写一两句：改了什么、哪个检查报了什么错。
