# Tyousa: 投币洗衣店选址评分表自动回填

一个可扩展的 Python 项目，用于将候选点位的地理/人口/竞品指标自动填入 Excel 评分模板（「候选点」sheet），让评分列自动计算。默认以大阪市示例模板为参考，可扩展到其他区域。

## 功能概览
- CLI（Typer）：`run` 端到端、`geocode`、`fetch-stats`、`fetch-poi`、`fill-excel`。
- StatsProvider：
  - `RichReportProvider`（已实现）：解析 jSTAT MAP 导出的 RichReport_xxx.xlsx 的「世帯数」sheet，用两圈层（１次ｴﾘｱ=600m，２次ｴﾘｱ=2km）计算 E~K 指标。
  - `JstatApiProvider`（占位）：留好接口以供后续接入官方 jSTAT MAP API。
- GoogleProvider（已实现）：调用 Google Maps Platform 的 Geocoding / Places API 计算竞品、车站、锚点、停车等指标，带最小字段、重试与缓存。
- ExcelWriter：按字段名映射 A~Y 列写入，不破坏公式/格式；可选择保留已有手工值。
- 缓存：SQLite，含 TTL（Geocode 30 天、Places 7 天，可扩展）。
- 测试：haversine 距离、RichReport 解析、Excel 写入百分比与行定位。

## 目录结构
- `src/tyousa/`：主代码，按 providers / utils / excel / cli 模块化。
- `example/`：示例候选点 CSV 与运行脚本（示例 Excel 由 CLI 生成，不再随仓库提供二进制）。
- `templates/`：模板占位目录。
- `.cache/`：运行时自动创建的 SQLite 缓存目录。

## 安装
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## 环境变量
复制 `.env.example` 后填入真实 key：
- `GOOGLE_API_KEY`：Google Maps Platform（Geocoding + Places）
- `JSTAT_API_KEY`：jSTAT MAP API（占位）
- `ESTAT_APP_ID`：e-Stat（预留给未来趋势指数）

## 输入数据（candidates.csv）
必备/可选列：
- `id`（可空，自动生成 OSK001..）
- `address`（可选，缺经纬度时需 Geocoding）
- `lat` / `lon`（可选，已知坐标可跳过 Geocoding）
- `richreport_path`（可选，指向每个点的 RichReport_xxx.xlsx；无 JSTAT_API_KEY 时必填）
- `notes`（可选）

示例：`example/candidates_example.csv`（含 3 个大阪点位 + RichReport 样例）。

## 模板要求
- 推荐通过 `python -m tyousa.cli prepare-samples --output-dir example` 生成示例模板与 RichReport（避免二进制提交）。生成后默认模板路径为 `example/template.xlsx`，RichReport 为 `example/richreport_sample.xlsx`。
- 模板 sheet 名为「候选点」，第 1 行是字段名，第 5 行起写入。
- 列名映射按中文字段识别，不依赖列号。
- 百分比列（G/H/I/J/K）写入 0~1 小数，保持 Excel 百分比格式正确。

## CLI 用法
所有命令均在项目根运行，示例：

### 生成示例模板 / RichReport（避免存储二进制）
```bash
python -m tyousa.cli prepare-samples --output-dir example
```

### 端到端（需要 Google API，可混合 RichReport）
```bash
python -m tyousa.cli run example/candidates_example.csv \
  --template-path example/template.xlsx \
  --richreport-root example \
  --preserve-manual-col True
```
输出：`outputs/metrics.csv`、`outputs/filled.xlsx`、`logs/run.log`。

### 仅 Geocoding
```bash
python -m tyousa.cli geocode "大阪府大阪市北区梅田3丁目1-1"
```

### 仅统计（无外部 key，可用 RichReport）
```bash
python -m tyousa.cli fetch-stats example/candidates_example.csv --richreport-root example
```

### 仅 POI（需 GOOGLE_API_KEY 且候选点有经纬度）
```bash
python -m tyousa.cli fetch-poi example/candidates_example.csv
```

### 仅回填 Excel（使用已有 metrics.csv/json）
```bash
python -m tyousa.cli fill-excel outputs/metrics.csv --template-path example/template.xlsx
```

示例脚本：`example/run_example.sh`（自动生成示例 Excel，使用 RichReport 样例跑通 fill-excel，无需外部 key）。

## 实现细节与假设
- **JstatApiProvider** 仍为占位，需参考官方 API 鉴权/区域定义后扩展；当前如设置 `JSTAT_API_KEY` 会抛出 `NotImplementedError`。
- Google Places 请求使用最小字段集，含重试（429/5xx）和指数退避；缓存 place 计数/距离结果 7 天，不缓存详情。
- TrendProvider 预留 e-Stat 扩展，目前返回 None。
- 主干道距离（T 列）留空，未来可通过 RoadProvider 插件填充。
- 当 2km 内无竞品时，`nearest_competitor_distance_m` 为空，避免伪造距离；可在 README/下游配置中决定是否使用自定义大值。

## 成本与配额提醒
- Google Places/Geocoding 按调用计费，请在 `.env` 设置有效 key 并限制 IP/配额。
- 使用示例 RichReport 不会访问外部网络，适合离线演示与测试。

## 常见问题
- 百分比列显示 6918%？请确保写入 0.6918 而非 69.18。
- Excel 公式未计算？请在 Excel 中启用自动计算或重新打开文件。
- 无 API Key 如何体验？使用 `example/run_example.sh`，仅依赖本地 RichReport 样例。

## 开发与测试
- 代码格式：`black .`
- Lint：`ruff check .`
- 测试：`pytest`

## 扩展点
- 在 `tyousa/providers/jstat_api.py` 填入官方调用逻辑（建议加入缓存与最小字段请求）。
- 在 `tyousa/providers/stats.py` 的 `TrendProvider` 中实现 e-Stat 行政区趋势指数。
- 在 `tyousa/providers/google_poi.py` 添加 Place Details + 强竞品判定（基于评分/评论数阈值）。
- 添加 RoadProvider 以计算主干道距离（OSM/商业数据皆可）。
