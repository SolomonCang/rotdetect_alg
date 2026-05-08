# Gamma Dor 型脉动变星渐近等周期间隔自动搜索方案

## 1. 项目目标

本项目面向 Kepler 与 TESS 光变曲线频谱分析后的频率列表，自动识别 gamma Dor 型脉动变星中高阶 g 模的渐近等周期间隔现象。

输入是一颗星的频率峰列表，至少包含：

- 频率 `f`
- 振幅 `A`
- 信噪比 `S/N`
- 频率误差 `sigma_f`，如果可得
- 峰来源标记，例如 Kepler、TESS、sector、quarter，若可得

输出是一组候选 g 模周期间隔序列：

- 最佳平均周期间隔 `Delta_P`
- `Delta_P` 不确定度
- 匹配到的周期列表
- 对应的相对径向阶编号 `n`
- `P-Delta P` 图中的斜率
- 模式数量 `N_modes`
- 周期覆盖范围 `coverage`
- 显著性或假警报概率 `FAP`
- 综合置信度 `confidence_score`
- 诊断图：`P-Delta P` 图与 period echelle 图

核心问题可以抽象为：在含有噪声峰、组合频率、谐波、漏检峰和旋转效应的周期集合中，寻找满足近似关系的子序列：

```text
P_n ~= P_0 + n * Delta_P
```

实际 gamma Dor 星中，受近核心旋转、化学梯度和模式俘获影响，相邻周期间隔并非严格常数，因此算法需要允许 `Delta P` 随周期缓慢变化。

## 2. 天体物理背景

高阶低频 g 模在渐近近似下具有近似等周期间隔：

```text
P_n,l ~= Pi_0 / sqrt(l(l + 1)) * (n + epsilon)
```

其中：

- `P_n,l` 是径向阶为 `n`、球谐度为 `l` 的模式周期。
- `Pi_0` 与恒星内部浮力频率结构有关。
- `Delta_P_l = Pi_0 / sqrt(l(l + 1))` 是对应 `l` 的渐近周期间隔。

在非旋转或弱旋转情形下，同一 `l, m` 模式序列在 `P-Delta P` 图中接近水平线；在旋转情形下，尤其对 gamma Dor 型星，序列常表现为带斜率的近似直线。顺行、逆行和轴对称模式的斜率和形态不同。

本项目第一阶段不直接做完整星震正演建模，而是完成稳健的自动探测：判断一颗星是否存在可信的渐近 g 模周期间隔序列，并给出可用于后续建模的候选参数。

## 3. 数据预处理

### 3.1 频率到周期转换

频率单位统一为 `d^-1`，周期单位统一为 `d`：

```text
P = 1 / f
sigma_P ~= sigma_f / f^2
```

需要剔除：

- `f <= 0` 的频率。
- 明显超出 gamma Dor g 模范围的频率。
- 误差或 S/N 不满足最低要求的峰。

建议初始搜索范围：

```text
0.3 d <= P <= 3.0 d
0.005 d <= Delta_P <= 0.08 d
```

实际范围应保留为配置项。Kepler 数据可用更低的噪声阈值，TESS 数据因时间跨度短、频率分辨率较差，默认阈值应更保守。

### 3.2 频率清洗

频率列表中常见污染包括：

- 谐波：`2f_i`, `3f_i`
- 组合频率：`f_i + f_j`, `|f_i - f_j|`
- 旋转调制或活动相关低频峰
- 仪器系统峰
- TESS sector 拼接带来的窗口函数残留

建议实现两层清洗：

1. 轻量清洗：只剔除已知坏峰和低 S/N 峰。
2. 保守标记：不直接删除疑似组合频率，而是降低权重。

权重可定义为：

```text
w_i = q_snr * q_amp * q_source * q_clean
```

其中：

- `q_snr` 随 S/N 增大而增大。
- `q_amp` 可使用振幅排序或归一化振幅。
- `q_source` 表示多数据源重复检出的可信度。
- `q_clean` 对疑似组合频率、谐波或仪器峰降权。

## 4. 总体算法流程

推荐采用三阶段流程：

```text
频率清洗
-> 周期转换
-> Delta_P 网格扫描
-> phase 聚集评分
-> top-k 候选 Delta_P
-> RANSAC 整数阶序列拟合
-> P-Delta P 线性趋势细化
-> bootstrap / shuffle 显著性评估
-> 输出候选序列和诊断图
```

这个组合兼顾速度和鲁棒性：

- 网格扫描负责快速生成候选 `Delta_P`。
- phase 聚集评分负责发现 period echelle 图中的 ridge。
- RANSAC 负责在大量离群峰中找出可信子序列。
- 线性趋势细化负责适配 gamma Dor 星常见的旋转斜率。
- bootstrap 或随机打乱负责估计假阳性概率。

## 5. 候选 Delta_P 扫描

### 5.1 period echelle 折叠

对每一个候选 `Delta_P`，计算周期相位：

```text
phi_i = (P_i / Delta_P) mod 1
```

若存在真实的等周期间隔序列，一组周期会在相位空间聚集，或在 period echelle 图中形成 ridge。

period echelle 图可使用：

```text
x_i = P_i mod Delta_P
y_i = P_i
```

其中 `x_i` 是折叠后的周期位置，`y_i` 是原始周期。严格等间隔序列表现为近似竖直 ridge；有旋转斜率时，ridge 会倾斜。

### 5.2 phase 聚集评分

最简单的聚集评分是 Rayleigh power：

```text
R(Delta_P) = |sum_i w_i * exp(2*pi*j*phi_i)| / sum_i w_i
```

`R` 越接近 1，说明相位越集中。但真实数据可能有倾斜 ridge，单纯相位聚集会漏检。因此建议同时计算局部窗口内的聚集：

```text
R_local(Delta_P) = max over period windows R_window
```

也可以使用相位熵：

```text
H = -sum_k p_k * log(p_k)
score_entropy = 1 - H / log(K)
```

其中 `K` 是相位分箱数。

初始候选评分：

```text
score_scan =
    a1 * R_global
  + a2 * R_local
  + a3 * entropy_score
  + a4 * weighted_peak_count
```

推荐保留 `top_k = 20-50` 个候选 `Delta_P`，并合并彼此过近的候选峰。

### 5.3 网格设置

`Delta_P` 网格步长需要小于典型残差容忍度。可按周期覆盖范围估计：

```text
delta_grid <= tolerance / N_order_span
N_order_span ~= (P_max - P_min) / Delta_P
```

第一版可使用固定步长：

```text
delta_grid = 1e-4 d
```

后续优化为两级扫描：

1. 粗扫：`1e-4 d` 到 `5e-4 d`
2. 细扫：围绕候选峰使用 `1e-5 d` 到 `5e-5 d`

## 6. RANSAC 整数阶序列拟合

### 6.1 基础模型

对每个候选 `Delta_P`，拟合：

```text
P_i = P_0 + n_i * Delta_P + epsilon_i
```

其中 `n_i` 是未知整数。由于绝对径向阶通常未知，可以只输出相对阶：

```text
n_i = round((P_i - P_0) / Delta_P)
```

### 6.2 RANSAC 步骤

1. 从周期集合中随机选取两个或三个点。
2. 根据点间距估计候选 `Delta_P` 或修正现有 `Delta_P`。
3. 为所有周期分配最近整数阶 `n_i`。
4. 计算残差：

```text
r_i = P_i - (P_0 + n_i * Delta_P)
```

5. 满足 `|r_i| < tolerance_i` 的点作为 inliers。
6. 使用 inliers 重新加权最小二乘拟合 `P_0` 与 `Delta_P`。
7. 记录最高分模型。

容忍度建议同时考虑观测误差和物理偏离：

```text
tolerance_i = max(k_sigma * sigma_P_i, tolerance_floor)
```

第一版可设置：

```text
tolerance_floor = 0.005 d 到 0.02 d
```

更合理的做法是让容忍度随 `Delta_P` 缩放：

```text
tolerance_floor = eta * Delta_P
eta = 0.05 到 0.20
```

### 6.3 漏阶处理

真实观测中经常漏掉部分径向阶，因此不要求相邻周期都被检出。对相邻 inliers 的阶差：

```text
gap_i = n_{i+1} - n_i
```

允许 `gap_i > 1`，但需要加入惩罚：

```text
gap_penalty = sum_i max(0, gap_i - 1)
```

如果连续漏阶过多，例如 `gap_i > 5`，应降低序列可信度或分裂为两条序列。

## 7. P-Delta P 趋势细化

### 7.1 构造相邻周期间隔

对 RANSAC 找到的 inliers，按相对阶 `n` 排序。若两点阶差为 1，则直接计算：

```text
Delta_P_i = P_{i+1} - P_i
P_mid_i = (P_{i+1} + P_i) / 2
```

若阶差为 `k > 1`，可使用平均间隔：

```text
Delta_P_i = (P_{i+1} - P_i) / k
```

并对该点降低权重。

### 7.2 线性模型

拟合：

```text
Delta_P(P) = Delta_P_0 + s * (P - P_ref)
```

其中：

- `Delta_P_0` 是参考周期附近的平均周期间隔。
- `s` 是 `P-Delta P` 图中的斜率。
- `P_ref` 可取匹配周期的加权均值。

若 `|s|` 显著大于 0，说明序列存在系统性倾斜，可能与近核心旋转有关。

### 7.3 二次模型作为可选项

对于快速旋转或周期范围较宽的星，线性模型可能不足。第二阶段可引入：

```text
Delta_P(P) = Delta_P_0 + s1 * (P - P_ref) + s2 * (P - P_ref)^2
```

但自动检测阶段建议默认只使用线性模型，避免过拟合。

## 8. 序列评分与置信度

最终评分应综合统计显著性和天体物理合理性。

建议评分项：

```text
N = 匹配模式数量
coverage = (max(P_inlier) - min(P_inlier)) / (P_search_max - P_search_min)
coherence = 1 - robust_std(residual / tolerance)
gap_score = exp(-lambda_gap * gap_penalty)
weight_score = mean(w_i of inliers)
slope_quality = 线性 P-Delta P 拟合优度
```

综合分数：

```text
confidence_score =
    b1 * log(1 + N)
  + b2 * coverage
  + b3 * coherence
  + b4 * gap_score
  + b5 * weight_score
  + b6 * slope_quality
  - b7 * complexity_penalty
```

初始判定阈值可设为：

- `N_modes >= 5`：最低可疑候选。
- `N_modes >= 8`：较可信候选。
- `coverage >= 0.3`：覆盖范围较好。
- `FAP <= 0.01`：统计显著。

这些阈值需要通过人工标注样本和注入恢复实验校准。

## 9. 显著性评估

### 9.1 周期随机打乱

保持周期数量、权重和搜索范围不变，随机生成同数量的周期，重复完整搜索流程，得到最高虚假评分分布。

```text
FAP = count(score_random >= score_real) / N_random
```

建议：

```text
N_random = 200 到 1000
```

### 9.2 保持频率窗口的随机化

对 TESS 或 Kepler 的频谱窗口影响明显的样本，完全均匀随机可能低估假阳性。可采用：

- 在局部周期窗口内随机重排周期。
- 保持相邻周期差分布的 bootstrap。
- 对频率而非周期随机化，再转换到周期。

### 9.3 注入恢复实验

为了评估完整 pipeline 的召回率，向真实背景峰列表中注入人工 g 模序列：

```text
P_n = P_0 + n * Delta_P + noise
Delta_P(P) = Delta_P_0 + s * (P - P_ref)
```

改变：

- 模式数量
- 漏检比例
- 残差幅度
- 斜率
- S/N 分布
- 污染峰数量

输出召回率、误报率和参数恢复偏差。

## 10. 多序列与模式混叠

一颗 gamma Dor 星可能存在多条序列，例如不同 `l, m` 模式。自动流程应支持多序列搜索：

1. 找到最高置信度序列。
2. 将该序列 inliers 标记为已使用，但不立即删除。
3. 对剩余峰或降权后的峰重新搜索。
4. 若新序列与旧序列共享过多点，合并或保留更高分者。

序列间关系可用于辅助判断：

```text
Delta_P_l=2 ~= Delta_P_l=1 / sqrt(3)
```

但第一版不应强制该关系，因为旋转会改变观测形态。

## 11. 建议的软件结构

建议 Python 包结构：

```text
rotdetect_alg/
  data.py              # 输入输出数据结构
  preprocess.py        # 频率清洗与周期转换
  scan.py              # Delta_P 网格扫描
  ransac.py            # 整数阶序列拟合
  refine.py            # P-Delta P 趋势拟合
  significance.py      # bootstrap / shuffle / injection tests
  score.py             # 统一评分函数
  plot.py              # 诊断图
  pipeline.py          # 单颗星端到端流程
  config.py            # 默认配置
tests/
  test_synthetic_recovery.py
  test_false_positive.py
  test_gap_handling.py
docs/
  asymptotic_gmode_period_spacing_search.md
```

核心数据结构：

```python
@dataclass
class FrequencyPeak:
    frequency: float
    amplitude: float | None = None
    snr: float | None = None
    frequency_error: float | None = None
    source: str | None = None
    quality_flag: str | None = None

@dataclass
class PeriodSpacingSequence:
    delta_p: float
    delta_p_error: float | None
    p0: float
    periods: list[float]
    radial_orders: list[int]
    residuals: list[float]
    slope: float | None
    n_modes: int
    coverage: float
    fap: float | None
    confidence_score: float
```

## 12. 第一版最小可用实现

第一版建议只实现端到端可跑通的稳健版本：

1. 输入 CSV：`frequency, amplitude, snr, frequency_error`
2. 转周期并按周期排序。
3. 使用固定 `Delta_P` 网格做 phase 聚集扫描。
4. 保留 top 20 个候选。
5. 对每个候选运行 RANSAC。
6. 输出最高分序列。
7. 生成两张 PNG：
   - `period_spacing.png`
   - `period_echelle.png`
8. 使用 200 次随机周期重排估计 FAP。

默认配置：

```text
period_min = 0.3 d
period_max = 3.0 d
delta_p_min = 0.005 d
delta_p_max = 0.08 d
delta_p_grid = 1e-4 d
min_modes = 5
good_modes = 8
tolerance_fraction = 0.10
top_k_candidates = 20
n_random_fap = 200
```

## 13. 验证标准

### 13.1 合成数据

必须通过以下合成测试：

- 无噪声等间隔序列：恢复 `Delta_P` 误差小于一个网格步长。
- 带 20% 漏检：仍能恢复主序列。
- 带 50% 随机污染峰：误差和 FAP 仍合理。
- 带线性斜率：能识别非零 `P-Delta P` 斜率。
- 纯随机峰：不应输出高置信度序列。

### 13.2 真实样本

建议收集三类人工标注样本：

- 文献中已确认有清晰周期间隔序列的 gamma Dor 星。
- 有疑似但不清晰序列的边界样本。
- 无明显 g 模序列或污染严重的负样本。

评估指标：

```text
precision = 自动候选中真实序列比例
recall = 已知真实序列被找回比例
delta_p_bias = Delta_P_auto - Delta_P_literature
mode_match_rate = 匹配周期与人工标注周期的重合率
```

## 14. 主要风险与应对

| 风险 | 表现 | 应对 |
| --- | --- | --- |
| 组合频率污染 | 假 ridge 或虚假 Delta_P | 组合频率降权，不直接删除 |
| TESS 时间跨度短 | 频率分辨率不足，周期误差大 | 使用更大容忍度和更严格 FAP |
| 快速旋转 | ridge 弯曲，线性模型不足 | 第一版标记低拟合质量，第二版加入二次模型 |
| 多模式混叠 | 多条序列交叉或共享峰 | 迭代搜索与共享点惩罚 |
| 过拟合随机峰 | 随机数据也出现短序列 | 使用 FAP、最小模式数和覆盖范围阈值 |

## 15. 推荐开发顺序

1. 写合成数据生成器。
2. 实现 period conversion 和基础清洗。
3. 实现 `Delta_P` phase 扫描。
4. 实现 RANSAC 序列拟合。
5. 实现评分函数。
6. 实现诊断图。
7. 加入随机化 FAP。
8. 用合成数据校准阈值。
9. 用少量真实星人工检查。
10. 批量运行 Kepler / TESS 样本。

## 16. 第二阶段扩展

第二阶段可以加入更物理的模型：

- 传统近似框架下的旋转 g 模 pattern 拟合。
- 同时估计近核心旋转频率。
- 区分 prograde、retrograde 和 zonal modes。
- 使用贝叶斯模型比较不同 `l, m` 序列。
- 使用图搜索或动态规划替代 RANSAC，以更好处理长缺口。
- 使用机器学习分类器对候选诊断图打分，但不应替代可解释的物理评分。

## 17. 推荐结论

本项目最稳妥的第一版算法是：

```text
Delta_P phase scan + RANSAC integer-sequence fitting + linear P-Delta P refinement + randomization FAP
```

它既能利用渐近等周期间隔的核心物理特征，又能适应 gamma Dor 星真实数据中的漏检、污染峰和旋转斜率。该方案输出的参数和诊断图也适合作为后续星震建模、人工复核和论文样本筛选的基础。
