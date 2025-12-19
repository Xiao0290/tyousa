你是 OpenAI Codex（coding agent）。请在当前仓库中从零搭建一个“投币洗衣店选址评分表自动回填”Python 项目，并确保可运行、可扩展、可维护。

# 0. 背景与目标
我有一份 Excel 模板（文件名示例：大阪市_20点位_模拟数据_评分表.xlsx
），其中 sheet「候选点」第 1 行是字段名，第 5 行起填候选点数据（公式预置到第 204 行）。我希望实现自动化：

输入：候选点地址（日本大阪市内为主）或经纬度（WGS84）。
输出：在原模板基础上生成一个新的 xlsx，自动把「候选点」sheet 的 A~Y 列（原始输入字段）尽可能自动填好，让后面的评分列（Z~）与总分/一票否决自动生效。

必须自动化的字段优先级：
- 必须：A~U（编号、地址、经纬度、人口/世带/住房结构、竞品数、最近竞品距离、车站/生活锚点距离、停车锚点）
- 可选/允许留空：V~Y（可视性、坪租、阻隔、夜间风险）——先做成“可手工补 + 可通过插件扩展”。

# 1. Excel 模板字段（以「候选点」sheet 第 1 行为准）
请不要硬编码列号，必须根据第 1 行的中文字段名做映射（但默认模板字段如下，便于你实现/测试）：
A 编号
B 区域名称
C 纬度
D 经度
E 600m内户数
F 2km内户数
G 600m内租赁户占比
H 2km内租赁户占比
I 600m内集合住宅占比
J 600m内小户型占比（单身+2人户）
K 2km内家庭户占比
L 人口趋势指数
M 600m内竞品数量
N 2km内竞品数量
O 最近竞品距离(米)
P 600m内强竞品(0/1)
Q 2km内强竞品(0/1)
R 到最近车站距离(米)
S 到生活锚点距离(米：超市/药妆/家居)
T 到主干道距离(米)
U 300m内停车锚点(0/1)
V 可视性评分(1-5)
W 坪租估计(円/坪)
X 阻隔评分(1-5)
Y 夜间风险评分(1-5)

重要：G/H/I/J/K 在模板里通常是“百分比格式”，写入数值必须是 0~1 的小数（例如 69.18% 要写 0.6918），否则会显示 6918% 并导致评分错误。

# 2. 数据来源与实现策略（必须同时支持两种统计来源）
## 2.1 官方统计（E~K）来源：StatsProvider 的两种实现
(1) 主要实现：jSTAT MAP API（推荐）
- 目标：给定 lat/lon + radii=[600,2000]，返回能计算出 E~K 的聚合统计（国势调查等）。
- 你需要在实现时查阅 jSTAT MAP 官方 API 文档并按其鉴权/参数实现。
- 将此实现命名为：JstatApiProvider
- 通过环境变量启用：JSTAT_API_KEY（或按官方要求的 key 名称）

(2) 备用实现：解析 RichReport Excel（我从 jSTAT MAP 导出的 RichReport_xxx.xlsx）
- 目标：如果用户没有 JSTAT_API_KEY，允许用户传入每个点对应的 RichReport 文件，你解析其中 sheet「世帯数」来得到 E~K。
- 在「世帯数」sheet 中，列标题包含 '１次ｴﾘｱ','２次ｴﾘｱ'；行包含：
  - 一般世帯総数
  - 単身世帯数 / ２人世帯数 / ３人世帯数 / ４人世帯数 / ５人世帯数 / ６人以上世帯数
  - 主世帯数、共同住宅世帯数
  - 住宅に住む一般世帯、持ち家世帯数（用于计算“非持家比率”近似租赁占比）
  - 民営の借家世帯数（可选用于更保守口径）
- 将此实现命名为：RichReportProvider

StatsProvider 输出统一的结构体/字典，至少包含下列原子指标（两圈层）：
- households_total (一般世帯総数)
- one_person, two_person, three_plus（或 3/4/5/6+ 分开）
- main_households (主世帯数)
- apartment_households (共同住宅世帯数)
- housing_households (住宅に住む一般世帯)
- owner_households (持ち家世帯数)
- private_rental_households (民営の借家世帯数，可选)

然后按统一算法计算写入 E~K：
E = households_total@600
F = households_total@2000
G = rental_share@600
H = rental_share@2000
I = apartment_households@600 / main_households@600
J = (one_person@600 + two_person@600) / households_total@600
K = (three_person@2000 + four_person@2000 + five_person@2000 + six_plus@2000) / households_total@2000

其中 rental_share 优先用“非持家比率”（更完整，避免缺少公営/UR 等类别导致低估）：
rental_share = (housing_households - owner_households) / housing_households
（若 owner/housing 缺失则 fallback 到 private_rental_households / housing_households）

## 2.2 Google 地图 POI（M~U, R~S）来源：GoogleProvider
必须使用 Google Maps Platform 官方 API（不要抓网页），通过环境变量提供 key：
GOOGLE_API_KEY

功能：
- Geocoding：地址 -> lat/lon（若输入已给 lat/lon 则跳过）
- Places：周边检索 / 文本检索，用于：
  - 竞品（コインランドリー）数量：600m、2km
  - 最近竞品距离：2km 内所有竞品取最小直线距离（haversine）
  - 车站距离：最近车站（type=train_station 或 keyword=駅）
  - 生活锚点距离：最近的“超市/药妆/家居”锚点（建议 types：supermarket / drugstore 或 pharmacy / home_goods_store；若 type 不稳定可用日文关键词搜索）
  - 停车锚点：300m 内是否有 parking（有则 1，否则 0）

输出：
M = count_competitors_600
N = count_competitors_2000
O = nearest_competitor_distance_m（若 2km 内无竞品则为空或一个约定的大值，并在 README 说明）
R = nearest_station_distance_m
S = nearest_anchor_distance_m
U = parking_anchor_300m (0/1)

强竞品（P/Q）：
- 先做成“可选自动判定”，默认策略：留空或 0（由用户人工复核）。
- 但框架要支持：若配置 strong_competitor.enabled=true，则对竞品 Top-N（比如按距离最近的 10 家）调用 Place Details（字段最小化）拿 rating、userRatingCount、openingHours 等，再用可配置阈值判定强竞品，并写入：
P：600m 内是否存在强竞品（0/1）
Q：2km 内是否存在强竞品（0/1）

注意成本控制：
- Places 请求必须使用最小 FieldMask，只取你计算所需字段（id/location/types/displayName/rating/userRatingCount 等）。
- 做缓存与去重，避免重复请求。

## 2.3 主干道距离（T）与 V~Y
- T（到主干道距离）先留空（None），但代码要预留插件接口 RoadProvider（例如 future 可接 OSM 或道路数据）。
- V~Y：保持可手工填写，CLI 提供 --preserve-manual-col 选项：如果目标单元格已有值则不覆盖。

## 2.4 人口趋势指数（L）
- L 先实现为可插拔 TrendProvider：
  - 默认：None（留空）
  - 可选实现：使用 e-Stat API 拉取行政区级（区/市）人口与世带在 2015 vs 2020 的变化率，生成指数：
    trend_index = (pop_2020-pop_2015)/pop_2015*100 + (hh_2020-hh_2015)/hh_2015*100
- 因为行政区识别需要 reverse geocode 或 JIS code 映射，请把这块做成独立模块，README 说明如何启用。
- 如果实现过重，可先只把框架搭好并给出 TODO + 说明。

# 3. 输入/输出与 CLI
实现一个 CLI（建议 Typer）：
- run: 端到端（geocode -> stats -> poi -> write excel）
- geocode: 只做地址到经纬度
- fetch-stats: 只拉 E~K 原子统计
- fetch-poi: 只拉 M~U/R~S 等 POI 指标
- fill-excel: 将已有的 metrics.json/csv 写入模板

输入格式（至少支持 CSV）：
candidates.csv columns:
- id（可选，若空则自动 OSK001..）
- address（可选）
- lat（可选）
- lon（可选）
- richreport_path（可选，用于 RichReportProvider）
- notes（可选）

输出：
- outputs/filled.xlsx（基于模板写入）
- outputs/metrics.csv 或 metrics.json（每个点的所有计算字段与中间字段）
- logs/run.log

写入策略：
- 自动找「候选点」sheet 第 5 行开始的空行写入（或按 id 匹配更新已有行）
- 不要破坏模板的公式、样式、冻结窗格等
- 仅写 A~Y（和你实现的可选列），不要改动 Z 之后的评分公式

# 4. 工程要求（必须）
- Python 3.11+
- 依赖管理：requirements.txt 或 pyproject.toml（推荐 pyproject + uv/poetry 均可）
- 代码结构清晰、模块化、可测试
- 实现稳健的：
  - HTTP 重试（429/5xx），指数退避
  - 超时与错误处理（某个点失败不影响其他点；输出错误摘要）
  - 本地缓存（建议 SQLite），并支持 TTL：
    - Geocode 缓存 30 天
    - Places：仅缓存 place_id 与你计算出来的派生值（count/distance/0-1），不要长期缓存店名/地址/评论等原始数据；如需缓存原始响应请设置 TTL <= 30 天 且默认关闭
    - jSTAT/e-Stat：缓存 90 天（统计数据不频繁变化）
- 单元测试（pytest）：
  - haversine 距离
  - RichReportProvider 解析（用 tests/fixtures 放一个小的示例 xlsx 或用最小 mock）
  - ExcelWriter 写入（验证百分比写入为小数、行定位、列映射）
  - API 层用 mock（不要在 CI 真实打外部 API）
- 代码质量：ruff/black（或等效工具），并在 README 说明如何运行检查
- 文档：README.md 至少包含：
  - 功能简介
  - 如何准备 API key（.env.example）
  - 如何准备 candidates.csv
  - 如何运行命令
  - 成本/配额注意事项（Google Places/Geocoding）
  - 常见问题（例如百分比列必须写 0~1、小样本导致分位数空白、Excel 需重新计算等）

# 5. 交付物（你必须产出）
1) 可运行的 Python 项目源码（按以上 CLI）
2) templates/ 目录示例（放模板文件占位说明；若仓库中已有模板则直接使用）
3) 一个 example/ 目录：
   - example/candidates_example.csv（至少 3 条大阪地址）
   - example/run_example.sh（或等效命令）
4) tests/ 完整可跑
5) .env.example（包含 GOOGLE_API_KEY、JSTAT_API_KEY、ESTAT_APP_ID 等占位）
6) AGENTS.md：写清楚本项目常用命令（安装、测试、lint、运行），让后续 Codex 更好协作

# 6. 验收标准（必须全部满足）
- 在没有任何 key 的情况下：用 RichReportProvider + fixtures 也能跑通 fill-excel（不报错，输出 xlsx）
- 在提供 GOOGLE_API_KEY 的情况下：geocode 和 fetch-poi 能对示例地址跑通（你可以在 README 中说明需要真实 key 才能运行）
- 写入后的 filled.xlsx：
  - 「候选点」A~Y 有值（至少 E~K + M~U + R~S）
  - 百分比列显示正确（0~100% 合理范围）
  - 评分列/总分列在 Excel 打开后能自动计算出结果（无需你手工改公式）

开始实现。请先生成项目骨架与 README，然后逐步实现 provider、pipeline、excel writer、tests。每完成一个阶段就运行本地测试并修复直到全绿。
若遇到不确定的外部 API 细节，请优先查官方文档，并把关键假设写入 README。
