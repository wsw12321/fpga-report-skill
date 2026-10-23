# 导出 RTL 原理图（PDF）。write_schematic 只在 GUI 模式下有效：batch 模式下它不报错，但什么也不输出。
#
# 用法（会短暂弹出一个 Vivado 窗口，导出后自动退出；非工程模式，不打开、不修改 .xpr）：
#   cd /d <一个临时目录>   （.Xil 等临时文件会生成在当前目录）
#   D:\Dev\FPGA\Vivado\2023.1\bin\vivado.bat -mode gui -nojournal -nolog -source <skill>/scripts/export_rtl.tcl ^
#       -tclargs <out_dir> <part> <src_dir> [<src_dir> ...] <top> [<top> ...]
#
#   <out_dir>  输出目录（必须已存在），每个 top 生成 <out_dir>/<top>.pdf；出错时写 <out_dir>/err.txt
#   <part>     器件型号，与工程一致，例如 xc7a100ticsg324-1L（看 runs/synth_1/*.tcl 中的 synth_design -part）
#   <src_dir>  源文件目录，读入其中的 *.v 和 *.sv；凡是“存在的目录”的参数都当作源文件目录
#   <top>      其余参数都当作要展开的模块名；每个模块单独 synth_design -rtl，参数取默认值
#
#   所有路径一律用正斜杠；参数中不要出现 ; , = 等字符（vivado.bat 会把它们当作分隔符）。
#   导出的 PDF 是把横向图画在纵向页面上，用 schematic_pdf2png.py 旋转、裁边后转成 PNG。

set out  [lindex $argv 0]
set part [lindex $argv 1]
set src_dirs {}
set tops {}
foreach a [lrange $argv 2 end] {
    if {[file isdirectory $a]} { lappend src_dirs $a } else { lappend tops $a }
}

proc read_sources {dirs} {
    foreach d $dirs {
        foreach f [glob -nocomplain -directory $d *.v]  { read_verilog $f }
        foreach f [glob -nocomplain -directory $d *.sv] { read_verilog -sv $f }
    }
}

set log [open $out/export_rtl.log w]
puts $log "argv: $argv"
puts $log "src_dirs: $src_dirs"
puts $log "tops: $tops"
if {[catch {
    foreach t $tops {
        # close_design 之后源文件列表可能被清空，每次展开前检查一下
        if {[llength [get_files -quiet]] == 0} { read_sources $src_dirs }
        puts $log "$t: [llength [get_files -quiet]] files: [get_files -quiet]"
        synth_design -rtl -top $t -part $part -name rtl_$t
        show_schematic [concat [get_cells] [get_ports] [get_nets]] -name sch_$t
        write_schematic -force -format pdf -orientation landscape -scope all -name sch_$t $out/$t.pdf
        close_design
    }
} err]} {
    puts $log "ERROR: $err\n$::errorInfo"
    set fh [open $out/err.txt w]
    puts $fh $err
    close $fh
}
close $log
exit
