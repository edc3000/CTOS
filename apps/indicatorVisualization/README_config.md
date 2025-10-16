# 参数热更新配置说明

## 概述
`draw_hedge_index.py` 现在支持通过配置文件进行参数热更新，无需修改代码即可调整所有关键参数。

## 配置文件
- **主配置文件**: `chart_config.json` (自动创建)
- **示例配置文件**: `chart_config_example.json`

## 使用方法

### 1. 首次运行
首次运行时会自动创建 `chart_config.json` 文件，包含所有默认参数。

### 2. 修改参数
直接编辑 `chart_config.json` 文件中的参数值，保存后重新运行程序即可生效。

### 3. 参数说明

#### 基础参数
- `top10_coins`: 前10币种列表
- `prex`: 文件名前缀
- `time_gap`: 时间周期 (如 '5m', '1h', '1d')
- `good_group`: 优质币种组
- `all_rate`: 权重配置
- `bad_coins`: 劣质币种列表

#### 布林带参数
- `bollinger_window`: 布林带窗口期 (默认: 20)
- `bollinger_std_multiplier`: 标准差倍数 (默认: 2.0)

#### 阈值参数
- `upper_threshold`: 高于中轨的阈值 (默认: 0.75)
- `lower_threshold`: 低于中轨的阈值 (默认: 0.25)

#### 技术分析参数
- `lookback`: 回看期数 (默认: 200)
- `n_sigma`: 标准差倍数 (默认: 2)
- `r2_threshold`: R²阈值 (默认: 0.50)
- `stack_window`: 堆叠窗口 (默认: 20)
- `stack_std_multiplier`: 堆叠标准差倍数 (默认: 2)

#### 成交量分析参数
- `vol_target_range_ratio`: 目标振幅比例 (默认: 0.5)

#### 拐点检测参数
- `pct_threshold`: 百分比阈值 (默认: 0.015)
- `half_window`: 半窗口大小 (默认: 10)

#### 图表参数
- `figsize`: 图表尺寸 [宽度, 高度] (默认: [16, 11])
- `height_ratios`: 子图高度比例 [上, 中, 下] (默认: [4, 2, 1])
- `dpi`: 图片分辨率 (默认: 150)

#### 颜色配置
- `unique_colors`: 颜色列表 (12种预设颜色)

#### 其他参数
- `max_configs_to_use`: 最大配置组数 (默认: 3)

## 参数验证
程序会自动验证参数的有效性：
- 阈值参数必须在 [0, 1] 范围内
- 窗口参数必须 ≥ 5
- 图表尺寸必须 > 0
- DPI 必须 > 0

无效参数会自动使用默认值并显示警告信息。

## 示例用法

```python
# 直接调用，使用配置文件参数
main1()

# 或者覆盖部分参数
main1(time_gap='1h', upper_threshold=0.8)
```

## 注意事项
1. 配置文件必须是有效的JSON格式
2. 修改参数后需要重新运行程序才能生效
3. 建议在修改前备份原配置文件
4. 参数验证失败时会使用默认值并显示警告


