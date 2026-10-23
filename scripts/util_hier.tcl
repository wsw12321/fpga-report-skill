# 从布线后的 checkpoint 生成分层资源报告（只读打开 .dcp，不修改工程）。
#
# 用法：
#   cd /d <一个临时目录>
#   D:\Dev\FPGA\Vivado\2023.1\bin\vivado.bat -mode batch -nojournal -nolog -source <skill>/scripts/util_hier.tcl ^
#       -tclargs <Lab-N.runs/impl_1/xxx_routed.dcp> <out.rpt>
#
# 解读时注意：综合默认 flatten_hierarchy = rebuilt，跨层次优化后，某些模块的逻辑会被计入别的实例名下
# （例如 Lab 2 中 bin2bcd 的 LUT 被计入了 timer_inst）。分层数字只能作参考，FF 数通常比 LUT 数更可靠。

set dcp [lindex $argv 0]
set rpt [lindex $argv 1]
open_checkpoint $dcp
report_utilization -hierarchical -file $rpt
puts "written $rpt"
