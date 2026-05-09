# rotdetect_alg

用于自动搜索 gamma Dor 型脉动变星高阶 g 模渐近等周期间隔序列的算法项目。

当前设计文档：

- [Gamma Dor 型脉动变星渐近等周期间隔自动搜索方案](docs/asymptotic_gmode_period_spacing_search.md)
- [RotDetect 具体实现架构文档](docs/implementation_architecture.md)

## 安装依赖

### 前置要求

- Python >= 3.11
- Node.js >= 18
- npm >= 10

### 后端依赖

后端使用 Python 包管理工具 `uv`。如果未安装，请先安装：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

然后安装后端依赖：

```bash
cd backend
uv sync
cd ..
```

或者使用 pip（如果不使用 uv）：

```bash
cd backend
pip install -e .
cd ..
```

### 前端依赖

安装前端依赖：

```bash
cd frontend
npm install
cd ..
```

## 本地启动

安装依赖后，可在项目根目录同时启动后端和前端：

```bash
python3 start_rotdetect.py
```

默认地址：

- 前端：`http://localhost:5173`
- 后端 API 文档：`http://localhost:8000/docs`

## 输入格式

支持 CSV / DAT / TXT。最简单可以只给一列周期或频率：

```text
period
0.812
0.843
0.875
```

或：

```text
frequency
1.2315
1.1863
1.1429
```

也支持无表头双列（常见 FFT 导出格式），默认解释为：

- 第一列：`frequency`（单位 d^-1）
- 第二列：`amplitude`

```text
1.2315 0.98
1.1863 0.91
1.1429 1.03
```

`amplitude`、`snr`、`frequency_error` 可以作为可选列提供。

前端会在上传文件后识别可用列，并提供 `Frequency column` 与
`Amplitude column` 下拉选择。对于无表头或注释表头的 DAT 文件，列会显示为
`Col 1`、`Col 2` 等形式，例如：

```text
# freq, ampl, phase, S/N
1.2221102501e+01 2.6609643593e-03 4.8532860519e+00 5.6808397050e+02
```

通常可选择：

- `Col 1` 作为 `frequency`
- `Col 2` 作为 `amplitude`

如果不手动选择，后端仍会尝试按列名或常见 FFT 导出格式自动推断。

## 当前算法要点

当前实现针对频率峰列表执行以下流程：

```text
输入表读取与列映射
-> S/N 与周期范围筛选
-> 按振幅保留最高峰
-> frequency -> period
-> 带斜率的 Delta_P 网格扫描
-> 整数阶序列拟合与一阶趋势细化
-> 按置信度、覆盖、模式数和振幅优先级排序
-> 输出候选序列、振幅分层周期范围和诊断图
```

振幅信息会进入三个位置：

- 峰列表按 `amplitude` 优先截断到 `max_peaks`。
- 扫描和拟合使用振幅/SNR 派生权重。
- 候选序列计算 `amplitude_score`，排序时高振幅序列会被优先考虑。

结果中还会给出 `amplitude_period_clusters`，按振幅把周期点分为高、中、低几层，并列出每层的周期范围。

## 关键参数

前端控制面板可直接调整：

- `period_min`, `period_max`：参与搜索的周期范围，单位 `d`。
- `delta_p_min`, `delta_p_max`, `delta_p_grid`：周期间隔搜索范围和步长，前端以秒显示。
- `min_modes`：候选序列至少包含的模式数。
- `max_peaks`：最多进入搜索的峰数，按振幅优先保留。
- `tolerance_fraction`：拟合残差容忍度相对 `Delta_P` 的比例。真实旋转斜率或模式俘获较明显时可适当放宽。
- `snr_threshold`：若输入包含 `snr` 或 `S/N` 列，低于该阈值的峰会被剔除。
- `Frequency column`, `Amplitude column`：显式指定输入表中哪两列作为频率和振幅。
- `a 图背景文件`：Candidate diagnostics 中 a 图黑色背景谱线的数据来源。留空时使用当前上传数据；也可填写仓库内相对路径，例如 `examples/KIC004253413_FFT_results.dat`。该背景文件只影响绘图，不参与搜索或排序。

## KIC004253413 示例

对 `examples/KIC004253413very_deep_clean.dat`，若目标是恢复人工确认的 19 个模式序列，推荐使用较聚焦的搜索窗口：

```text
period_min = 0.49 d
period_max = 0.72 d
delta_p_min = 0.006 d
delta_p_max = 0.016 d
delta_p_grid = 0.00005 d
max_peaks = 200
top_k_candidates = 20
tolerance_fraction = 0.15
snr_threshold = 4.0
frequency_column = col1
amplitude_column = col2
```

在该配置下，自动检测序列与
`examples/KIC004253413MCMC_emcee_best_No_3_certain_period=0.655010752927_period_series_after_manual_confirmation.dat_improve_series`
的第二列逐点一致。该文件第二列数值范围为 `0.5105-0.7075 d`，在当前项目中应按周期 `P` 解释；若当作频率再取倒数，会落到 `1.41-1.96 d`，与该序列不匹配。
