<#
用 xsim 命令行编译并运行一个或多个 testbench，导出 VCD 供 vcd_wave.py 绘图。不打开、不修改 Vivado 工程。

用法（PowerShell）：
  & <skill>\scripts\run_xsim.ps1 -Project D:\...\exp-2\Lab-2 -Tops tb_units,tb_lab_2 `
      [-TclDir D:\...\Lab-2\sim_tools] [-Extra D:\...\UTUandTOP\top.v,D:\...\utu.v] `
      [-Vivado D:\Dev\FPGA\Vivado\2023.1] [-NoVcd]

- 源文件：<Project>\<xxx>.srcs\sources_1\new 和 sim_1\new 下的 *.v / *.sv，再加上 -Extra 指定的文件。
  .v 按 Verilog 编译，.sv 按 SystemVerilog 编译。
- 每个 top：如果 <TclDir>\<top>.tcl 存在，就用它（自己决定导出哪些内部信号）；
  否则自动生成：把 top 这一层的全部信号导出到 <top>.vcd，然后 run all。
- 输出目录：<Project>\<xxx>.sim\cli\（Vivado 工程的 .gitignore 通常会忽略 *.sim）。
- 结束后打印每个 log 中以 "[" 开头的行和 $finish 行。xsim 的退出码不反映 testbench 的 PASS / FAIL，要看 log。
#>
param(
    [Parameter(Mandatory)] [string]   $Project,
    [Parameter(Mandatory)] [string[]] $Tops,
    [string]   $TclDir = '',
    [string[]] $Extra = @(),
    [string]   $Vivado = 'D:\Dev\FPGA\Vivado\2023.1',
    [switch]   $NoVcd
)
$ErrorActionPreference = 'Stop'
$Project = (Resolve-Path $Project).Path
$srcs = Get-ChildItem $Project -Directory -Filter '*.srcs' | Select-Object -First 1
if (-not $srcs) { throw "no *.srcs directory under $Project" }
$base = $srcs.Name -replace '\.srcs$', ''    # 目录的 BaseName 不会去掉 .srcs 后缀

$files = @()
foreach ($sub in 'sources_1\new', 'sim_1\new') {
    $d = Join-Path $srcs.FullName $sub
    if (Test-Path $d) {
        $files += @(Get-ChildItem $d -File | Where-Object { $_.Extension -in '.v', '.sv' }).FullName
    }
}
$files += @($Extra | Where-Object { $_ } | ForEach-Object { (Resolve-Path $_).Path })
$vFiles  = @($files | Where-Object { $_ -like '*.v' })
$svFiles = @($files | Where-Object { $_ -like '*.sv' })

$out = Join-Path $Project "$base.sim\cli"
$bin = Join-Path $Vivado 'bin'
New-Item -ItemType Directory -Force $out | Out-Null
Push-Location $out
try {
    if ($vFiles.Count) {
        & "$bin\xvlog.bat" @vFiles
        if ($LASTEXITCODE) { throw 'xvlog (Verilog) failed, see xvlog.log' }
    }
    if ($svFiles.Count) {
        & "$bin\xvlog.bat" -sv @svFiles
        if ($LASTEXITCODE) { throw 'xvlog (SystemVerilog) failed, see xvlog.log' }
    }
    foreach ($top in $Tops) {
        # 设计源文件常常没有 `timescale：与 Vivado 工程模式一样用 --relax，并给出默认时间单位
        & "$bin\xelab.bat" $top --relax -timescale 1ns/1ps -debug typical -s "${top}_sim"
        if ($LASTEXITCODE) { throw "xelab $top failed, see xelab.log" }

        $tcl = if ($TclDir) { Join-Path $TclDir "$top.tcl" } else { '' }
        if (-not ($tcl -and (Test-Path $tcl))) {
            $tcl = Join-Path $out "${top}_auto.tcl"
            $body = if ($NoVcd) { "run all`nquit`n" } else {
                "open_vcd $top.vcd`nlog_vcd [get_objects /$top/*]`nrun all`nclose_vcd`nquit`n"
            }
            Set-Content -Encoding ascii $tcl $body
        }
        # Tcl 会把反斜杠当转义符，脚本路径一律改用正斜杠
        & "$bin\xsim.bat" "${top}_sim" -tclbatch ($tcl -replace '\\', '/') -log "$top.log"
        if ($LASTEXITCODE) { throw "xsim $top failed, see $top.log" }
    }
} finally {
    Pop-Location
}

foreach ($top in $Tops) {
    "===== $top  ($out\$top.log)"
    Get-Content (Join-Path $out "$top.log") | Where-Object { $_ -match '^\[|\$finish|FATAL|Error:' }
}
