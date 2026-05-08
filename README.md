# rotdetect_alg

用于自动搜索 gamma Dor 型脉动变星高阶 g 模渐近等周期间隔序列的算法项目。

当前设计文档：

- [Gamma Dor 型脉动变星渐近等周期间隔自动搜索方案](docs/asymptotic_gmode_period_spacing_search.md)
- [RotDetect 具体实现架构文档](docs/implementation_architecture.md)

## 本地启动

安装依赖后，可在项目根目录同时启动后端和前端：

```bash
python3 start_rotdetect.py
```

默认地址：

- 前端：`http://localhost:5173`
- 后端 API 文档：`http://localhost:8000/docs`

## 输入格式

第一版前端上传 CSV，只需要一列周期或频率：

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

`amplitude`、`snr`、`frequency_error` 可以作为可选列提供。
