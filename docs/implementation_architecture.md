# RotDetect 最小可用实现架构文档

## 1. 第一版目标

第一版只实现最基本、可跑通、可交互检查的单颗星分析流程：

```text
用户在前端上传一颗星的周期或频率 CSV
        |
        v
前端点击“分析”
        |
        v
Python 后端读取周期 / 频率并搜索 g 模周期间隔
        |
        v
前端显示最佳候选序列、period echelle 图和 P-Delta P 图
```

第一版不做批量分析、不做用户系统、不做数据库、不做后台队列、不做复杂复核流程。目标是先证明核心算法和交互链路可以工作。

## 2. 输入与输出

### 2.1 输入文件

前端上传一个 CSV / DAT / TXT 文件，表示一颗星的周期列表、频率峰列表或频谱表。

第一版最小输入只需要一列。

格式 A：周期列表

```text
period
0.812
0.843
0.875
```

其中：

- `period`：周期，单位默认 `d`。

格式 B：频率列表

```text
frequency
1.2315
1.1863
1.1429
```

其中：

- `frequency`：频率，单位默认 `d^-1`。

可选列：

```text
frequency,amplitude,snr,frequency_error
1.2315,0.42,8.7,0.00002
1.1863,0.31,6.4,0.00003
```

如果没有 `amplitude` 列，后端把每一行视为已提取的模式频率或周期，并使用默认权重。若提供 `amplitude`，则在排序和权重计算中使用它。完整频谱表仍可使用 `frequency,amplitude` 输入，此时后端可做简单峰提取。

对于无表头或注释表头的 DAT 文件，前端会生成 `Col 1`、`Col 2` 等列选项。用户可以显式指定：

```text
frequency_column = col1
amplitude_column = col2
```

若不指定，后端按列名和常见 FFT 导出格式自动推断。Candidate diagnostics 的 a 图还支持一个可选背景文件路径 `spectrum_background_path`，该文件只用于绘制黑色背景谱线，不参与搜索。

### 2.2 输出结果

后端返回一个 JSON，前端直接用它渲染页面：

```json
{
  "status": "ok",
  "input_summary": {
    "n_rows": 1280,
    "n_peaks": 54,
    "input_quantity": "period",
    "has_amplitude": false,
    "frequency_min": 0.1,
    "frequency_max": 5.0
  },
  "best_sequence": {
    "delta_p": 0.03142,
    "delta_p_error": 0.00008,
    "p0": 0.812,
    "slope": -0.0021,
    "n_modes": 12,
    "coverage": 0.47,
    "confidence_score": 0.86,
    "periods": [0.812, 0.843, 0.875],
    "radial_orders": [0, 1, 2],
    "residuals": [0.0004, -0.0008, 0.0002]
  },
  "candidates": [],
  "plots": {
    "echelle": {},
    "period_spacing": {},
    "scan": {},
    "spectrum": {}
  },
  "warnings": []
}
```

第一版可以不计算严格 FAP，先用 `confidence_score`、`n_modes` 和 `coverage` 给出候选可信度。FAP 随机化留到第二版。

## 3. 技术选型

### 3.1 后端

第一版后端使用：

| 模块 | 技术 | 用途 |
| --- | --- | --- |
| Web API | FastAPI | 接收上传文件并返回分析结果 |
| 数据模型 | Pydantic | 校验请求和响应 |
| 表格读取 | pandas | 读取 CSV |
| 数值计算 | NumPy, SciPy | 峰提取、扫描、拟合 |
| 图数据 | Plotly JSON 兼容结构 | 前端交互图 |
| 测试 | pytest | 合成数据和 API 测试 |

不引入 Celery、Redis、SQLite。一次点击对应一次 HTTP 请求。若后续单次分析时间超过 10 到 20 秒，再改成异步任务。

### 3.2 前端

第一版前端使用：

| 模块 | 技术 | 用途 |
| --- | --- | --- |
| 应用框架 | React + Vite + TypeScript | 单页交互应用 |
| 请求 | fetch 或 Axios | 调用 `/api/analyze` |
| 图表 | Plotly.js | echelle、`P-Delta P` 和扫描曲线 |
| 样式 | 普通 CSS 或轻量组件 | 保持界面简单 |

前端只做文件上传、参数填写、点击分析和结果展示，不实现任何科学算法。

## 4. 最小目录结构

```text
rotdetect_alg/
  backend/
    pyproject.toml
    rotdetect/
      __init__.py
      api.py
      schemas.py
      core/
        data.py
        config.py
        preprocess.py
        peaks.py
        scan.py
        ransac.py
        refine.py
        score.py
        pipeline.py
        plot_payloads.py
    tests/
      test_pipeline_synthetic.py
      test_api_analyze.py
  frontend/
    package.json
    index.html
    src/
      main.tsx
      App.tsx
      api.ts
      types.ts
      components/
        UploadPanel.tsx
        ResultSummary.tsx
        CandidateTable.tsx
        DiagnosticCharts.tsx
      styles.css
  docs/
    asymptotic_gmode_period_spacing_search.md
    implementation_architecture.md
```

第一版所有后端 API 可以先放在 `backend/rotdetect/api.py`，等接口变多后再拆分路由。

## 5. 后端实现

### 5.1 核心数据结构

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SpectrumPoint:
    frequency: float
    amplitude: float = 1.0

@dataclass(frozen=True)
class FrequencyPeak:
    frequency: float
    amplitude: float = 1.0
    snr: float | None = None
    frequency_error: float | None = None

@dataclass(frozen=True)
class SearchConfig:
    period_min: float = 0.3
    period_max: float = 3.0
    delta_p_min: float = 0.005
    delta_p_max: float = 0.08
    delta_p_grid: float = 1e-4
    min_modes: int = 5
    top_k_candidates: int = 20
    tolerance_fraction: float = 0.10
    max_peaks: int = 200
    peak_threshold_factor: float = 4.0
    snr_threshold: float = 4.0
    frequency_column: str | None = None
    amplitude_column: str | None = None
    spectrum_background_path: str | None = None

@dataclass(frozen=True)
class PeriodSpacingSequence:
    delta_p: float
    delta_p_error: float | None
    p0: float
    periods: list[float]
    amplitudes: list[float]
    radial_orders: list[int]
    residuals: list[float]
    slope: float | None
    n_modes: int
    coverage: float
    confidence_score: float
    amplitude_score: float
    amplitude_mean: float
    amplitude_median: float

@dataclass(frozen=True)
class AmplitudePeriodCluster:
    rank: int
    label: str
    n_points: int
    period_min: float
    period_max: float
    amplitude_min: float
    amplitude_max: float
    amplitude_mean: float
    amplitude_median: float
    amplitude_fraction: float
    period_ranges: list[dict]

@dataclass(frozen=True)
class AnalysisResult:
    input_summary: dict
    best_sequence: PeriodSpacingSequence | None
    candidates: list[PeriodSpacingSequence]
    amplitude_period_clusters: list[AmplitudePeriodCluster]
    plots: dict
    warnings: list[str]
```

### 5.2 后端 pipeline

第一版 pipeline：

```text
读取 CSV / DAT / TXT
-> 应用显式列映射，或自动推断 period / frequency / amplitude / snr
-> 判断输入是 period 单列、frequency 单列，还是带 amplitude 的频谱 / 峰列表
-> 如果只有 period，转换为 frequency = 1 / period
-> 如果没有 amplitude，使用默认 amplitude = 1.0
-> 如果是完整频谱表，做简单峰提取
-> 按 S/N、振幅优先级和周期范围筛选峰
-> frequency -> period
-> 带斜率的 Delta_P 网格扫描
-> 取 top-k Delta_P 候选
-> 对每个候选做整数阶序列拟合、链选择和每阶去重
-> 对候选做 P-Delta P 线性趋势拟合
-> 计算 confidence_score 和 amplitude_score
-> 按置信度、振幅优先级、模式数和覆盖范围排序
-> 计算振幅分层周期范围
-> 可选读取 spectrum_background_path 作为 a 图背景
-> 生成前端图表 payload
-> 返回 JSON
```

### 5.3 简单峰提取

只有当输入包含 `frequency,amplitude` 且行数明显多于 `max_peaks` 时，才启用简单峰提取。若输入只有 `period` 或 `frequency` 单列，则直接视为已经提取好的模式列表。

第一版峰提取只做保守版本：

```text
1. 按 frequency 升序排列。
2. 找局部极大值：amplitude[i] > amplitude[i-1] 且 amplitude[i] > amplitude[i+1]。
3. 估计背景噪声：median(amplitude)。
4. 保留 amplitude >= threshold_factor * median(amplitude) 的点。
5. 按 amplitude 降序保留最多 max_peaks 个峰。
```

默认参数：

```text
threshold_factor = 4.0
max_peaks = 200
```

如果输入表已经包含 `snr`，则优先使用：

```text
snr >= 4.0
```

进入搜索的点会使用振幅和 S/N 派生权重：

```text
amp_weight = sqrt(max(amplitude, 0) / median(positive_amplitude))
snr_weight = sqrt(snr / snr_threshold)
weight = clip(amp_weight * snr_weight, 0.2, 5.0)
```

该权重参与 `Delta_P` scan、序列链选择、候选评分和振幅优先排序。

这一版峰提取不是最终科学方案，只作为兼容 `frequency,amplitude` 频谱表的补充能力。最小主流程仍是“输入周期或频率单列 -> 点击分析”。

### 5.4 API

只需要一个核心接口：

```http
POST /api/analyze
Content-Type: multipart/form-data

file=<periods.csv 或 frequencies.csv>
config={
  "period_min": 0.3,
  "period_max": 3.0,
  "delta_p_min": 0.005,
  "delta_p_max": 0.08,
  "delta_p_grid": 0.0001,
  "min_modes": 5,
  "top_k_candidates": 20,
  "tolerance_fraction": 0.10,
  "max_peaks": 200,
  "peak_threshold_factor": 4.0,
  "snr_threshold": 4.0,
  "frequency_column": "col1",
  "amplitude_column": "col2",
  "spectrum_background_path": "examples/KIC004253413_FFT_results.dat"
}
```

响应：

```json
{
  "status": "ok",
  "input_summary": {
    "n_rows": 1280,
    "n_peaks": 54
  },
  "best_sequence": {
    "delta_p": 0.03142,
    "delta_p_start": 0.0321,
    "delta_p_mid": 0.03142,
    "delta_p_end": 0.0307,
    "n_modes": 12,
    "coverage": 0.47,
    "confidence_score": 0.86,
    "amplitude_score": 0.91,
    "periods": [0.812, 0.843, 0.875],
    "amplitudes": [0.42, 0.31, 0.28],
    "radial_orders": [0, 1, 2],
    "residuals": [0.0004, -0.0008, 0.0002],
    "slope": -0.0021
  },
  "candidates": [],
  "amplitude_period_clusters": [],
  "plots": {
    "echelle": {
      "data": [],
      "layout": {}
    },
    "period_spacing": {
      "data": [],
      "layout": {}
    },
    "scan": {
      "data": [],
      "layout": {}
    },
    "spectrum": {
      "data": [],
      "layout": {}
    }
  },
  "warnings": []
}
```

错误响应：

```json
{
  "status": "error",
  "message": "CSV must contain either a frequency column or a period column.",
  "warnings": []
}
```

### 5.5 FastAPI 入口

```python
from fastapi import FastAPI, File, Form, UploadFile

app = FastAPI(title="RotDetect API")

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), config: str = Form("{}")):
    table = await file.read()
    search_config = parse_config(config)
    result = run_pipeline_from_csv_bytes(table, search_config)
    return result
```

第一版可以同步执行。前端点击后按钮进入 loading 状态，等待接口返回。

## 6. 前端实现

### 6.1 单页布局

第一版只有一个页面：

```text
顶部：RotDetect 标题

左侧控制区：
  - 上传 CSV / DAT / TXT
  - 输入列选择
  - 参数设置
  - a 图背景文件路径
  - 分析按钮
  - 输入摘要 / 错误提示

右侧结果区：
  - 最佳候选摘要
  - 振幅分层周期范围
  - 候选序列表
  - Candidate diagnostics 三联图
  - period echelle 图
  - Local Delta_P 图
  - Delta_P scan 图
```

### 6.2 前端状态

```typescript
type AnalyzeState =
  | { status: "idle" }
  | { status: "ready"; file: File }
  | { status: "running"; file: File }
  | { status: "success"; result: AnalysisResult }
  | { status: "error"; message: string };
```

### 6.3 用户流程

```text
1. 用户打开 http://localhost:5173
2. 上传一颗星的 periods.csv 或 frequencies.csv
3. 前端显示文件名和默认参数
4. 用户点击“分析”
5. 前端 POST /api/analyze
6. 分析按钮显示 loading，避免重复提交
7. 后端返回结果
8. 前端显示最佳 Delta_P、模式数量、置信度和诊断图
```

### 6.4 参数控件

第一版暴露少量关键参数：

| 参数 | 默认值 | 前端控件 |
| --- | --- | --- |
| `period_min` | `0.3` | number input |
| `period_max` | `3.0` | number input |
| `delta_p_min` | `0.005` | number input |
| `delta_p_max` | `0.08` | number input |
| `delta_p_grid` | `0.0001` | select 或 number input |
| `min_modes` | `5` | number input |
| `max_peaks` | `200` | number input |
| `tolerance_fraction` | `0.10` | number input |
| `snr_threshold` | `4.0` | number input |
| `frequency_column` | auto | select |
| `amplitude_column` | auto | select |
| `spectrum_background_path` | empty | text input |

暂不暴露 RANSAC 内部评分权重和 FAP 参数，以免界面过重。

### 6.5 结果展示

最佳候选摘要显示：

```text
Delta_P
N_modes
coverage
confidence_score
amplitude_score
amplitude_median
slope
```

候选序列表显示：

```text
rank
Delta_P
N_modes
coverage
confidence_score
amplitude_score
slope
```

图表：

- Candidate diagnostics：a 图为背景频谱/峰包络、峰点和序列点；b 图为局部 `Delta_P`；c 图为相对线性序列的残差。
- period echelle：横轴 `P mod Delta_P`，纵轴 `P`。
- Local `Delta_P`：横轴周期中点，纵轴相邻周期间隔。
- `Delta_P scan`：横轴候选 `Delta_P`，纵轴扫描分数或趋势扫描热图。

点击候选序列表中的一行时，前端切换对应候选的图表数据。第一版如果后端只返回最佳候选，也可以先只展示最佳候选。

## 7. 图表 payload

为了让前端实现简单，后端直接返回 Plotly 兼容结构。

```json
{
  "data": [
    {
      "type": "scatter",
      "mode": "markers",
      "x": [0.001, 0.010, 0.025],
      "y": [0.812, 0.843, 0.875],
      "marker": {
        "color": ["#2563eb", "#2563eb", "#dc2626"]
      },
      "text": ["n=0 residual=0.0004", "n=1 residual=-0.0008"]
    }
  ],
  "layout": {
    "xaxis": {"title": "P mod Delta_P [d]"},
    "yaxis": {"title": "P [d]"}
  }
}
```

后端保留原始数值字段，Plotly payload 用于直接画图：

```json
{
  "plots": {
    "echelle": {"data": [], "layout": {}},
    "period_spacing": {"data": [], "layout": {}},
    "scan": {"data": [], "layout": {}},
    "spectrum": {"data": [], "layout": {}}
  }
}
```

## 8. 本地启动

后端：

```bash
cd backend
uv sync
uv run uvicorn rotdetect.api:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

前端访问：

```text
http://localhost:5173
```

后端 API：

```text
http://localhost:8000/docs
```

前端开发环境通过 Vite proxy 把 `/api` 转发到 `http://localhost:8000`。

## 9. 最小验收标准

### 9.1 后端验收

- 能读取只包含 `period` 一列的 CSV。
- 能读取只包含 `frequency` 一列的 CSV。
- 能读取注释表头或无表头 DAT，并支持显式列映射。
- 若提供 `frequency,amplitude` 频谱表，能从频谱中提取一组峰。
- 能对提取峰执行 `Delta_P` 扫描和 RANSAC 拟合。
- 能使用振幅/SNR 权重并返回 `amplitude_score` 与振幅分层范围。
- 能使用可选背景文件生成 `spectrum` 图 payload。
- 对合成数据可恢复注入的 `Delta_P`。
- `/api/analyze` 返回结构化结果和 Plotly 图表 payload。

### 9.2 前端验收

- 能上传 CSV。
- 能上传 CSV / DAT / TXT。
- 能选择频率列和振幅列。
- 能修改基本搜索参数。
- 能设置 a 图背景文件路径。
- 点击“分析”后能调用后端。
- 分析期间有 loading 状态。
- 成功后显示最佳候选摘要。
- 成功后显示 period echelle、`P-Delta P` 和扫描曲线。
- 错误时能显示后端错误信息。

### 9.3 端到端验收

```text
准备一个合成 periods.csv 或 frequencies.csv
-> 打开前端
-> 上传文件
-> 点击分析
-> 等待结果
-> 页面显示 Delta_P 接近注入值
-> 诊断图中 inlier 点被高亮
```

## 10. 暂不实现内容

以下能力不进入第一版：

- 批量星表分析。
- 登录、权限和多人协作。
- SQLite / PostgreSQL 结果库。
- Celery / Redis 后台任务。
- FAP 随机化显著性评估。
- 人工复核状态保存。
- FITS 文件读取。
- 复杂 prewhitening。
- 多序列自动拆分。
- 传统近似下的旋转模式物理拟合。

这些内容等单颗星交互分析闭环稳定后再逐步加入。

## 11. 后续扩展路径

第一版稳定后，推荐按以下顺序扩展：

1. 增加结果保存目录，保留输入文件、配置和 JSON 结果。
2. 增加异步任务状态，支持长时间 FAP 估计。
3. 增加运行列表和历史结果查看。
4. 增加人工复核标记。
5. 增加批量分析 CLI。
6. 增加更严格的频率清洗、组合频率降权和显著性评估。
