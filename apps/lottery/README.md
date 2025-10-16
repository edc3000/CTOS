# 可追溯抽奖程序（Weighted Lottery with Audit Chain）

一个**单文件可执行**的抽奖脚本，支持「因子→权重」配置、参与者因子序列、**加权随机无放回抽样**，并将全过程记录为**区块链式哈希链（审计链）**，任何人都可**验证与复现**。

---

## 目录
- [特性](#特性)
- [需要的文件](#需要的文件)
- [快速开始](#快速开始)
- [如何配置 `config.json`](#如何配置-configjson)
- [运行抽奖](#运行抽奖)
- [验证与溯源](#验证与溯源)
- [对比配置一致性（`--verify-config`）](#对比配置一致性--verify-config)
- [复现过去任意一次结果](#复现过去任意一次结果)
- [多期活动使用方式](#多期活动使用方式)
- [隐私与合规建议](#隐私与合规建议)
- [常见问题](#常见问题)
- [示例 `config.sample.json`](#示例-configsamplejson)

---

## 特性
- **权重可配置**：例如 `follow/repost/like/reply` 分别赋予 10/10/2/5 权重；同一因子可重复出现（权重累加）。  
- **公平抽样**：采用 *Efraimidis–Spirakis* 的**加权无放回抽样**算法。  
- **可复现/可追溯**：
  - `deterministic` 模式：同配置 + 种子 → 结果可完全复现；
  - `system` 模式：每次引入系统熵，但**把本次种子写入审计链**，仍可复盘；
  - 全程写入**审计链**（哈希链），篡改即检出。  
- **极简依赖**：仅用 Python 标准库（Python 3.8+）。

---

## 需要的文件
- `lottery.py`：抽奖主脚本（单文件实现）。
- `config.json`：配置（抽奖人数、权重、参与者及其因子序列、随机种子策略）。
- （运行后自动生成）`winners.csv`：中奖结果。
- （运行后自动生成）`audit_chain.jsonl`：审计链（append-only 哈希链，记录配置/代码哈希、随机种子、结果哈希等）。

> 建议仓库结构：
```
your-lottery/
├─ lottery.py
├─ config.sample.json
├─ README.md
└─ LICENSE
```

---

## 快速开始
```bash
python3 --version      # 3.8+
cp config.sample.json config.json
# 编辑 config.json => 填写参与者、因子与权重、num_winners、seed 配置
python3 lottery.py --config config.json --winners-out winners.csv --audit-chain audit_chain.jsonl
python3 lottery.py --verify --audit-chain audit_chain.jsonl
# 如需进一步核对当前 config.json 是否与最近一次抽奖一致：
python3 lottery.py --audit-chain audit_chain.jsonl --verify-config config.json
```

---

## 如何配置 `config.json`

`config.json` 由三部分组成：

### 1) `draw` —— 抽奖参数
```json
"draw": {
  "num_winners": 3,                  // 要抽取的中奖人数
  "seed_mode": "deterministic",      // "deterministic" 或 "system"
  "manual_seed": "event-2025-10-16", // 建议用活动ID/期号
  "external_entropy": ""             // 可选：公共随机源（如区块哈希/NIST beacon），增强不可预测性
}
```
- `deterministic`：由「配置内容 + manual_seed + external_entropy」导出随机种子 → **同配置可复现**；  
- `system`：使用系统熵生成一次性随机种子，并**写入审计链**，便于事后回放。

### 2) `factors` —— 因子→权重
```json
"factors": {
  "follow": 10,
  "repost": 10,
  "like": 2,
  "reply": 5
}
```
- 可自行扩展与修改；**未知因子将被忽略（权重按 0 计）**。

### 3) `participants` —— 参与者及其因子序列
```json
"participants": [
  {"id": "alice", "factors": ["follow", "repost", "like"]},
  {"id": "bob",   "factors": ["reply", "reply", "like"]},
  {"id": "charlie", "factors": []}
]
```
- **同一因子可重复出现**以表示多次行为或更强权重（会按次数累加）；  
- 若某参与者总权重为 0，但名额尚未抽满，会在 0 权重用户中**均匀随机**补齐。

---

## 运行抽奖
```bash
python3 lottery.py   --config config.json   --winners-out winners.csv   --audit-chain audit_chain.jsonl
```
- 运行完成后，终端会打印**最后区块哈希**（last block hash）。
- 建议将该哈希**公开作为锚点**（例如 Git 提交/推文/群公告/链上 memo），便于外部核验。

---

## 验证与溯源
**A. 验证审计链未被篡改**
```bash
python3 lottery.py --verify --audit-chain audit_chain.jsonl
```
该命令只校验 `audit_chain.jsonl` 的**链结构完整性**（区块 `hash`、`prev_hash` 串联、索引等），与当前磁盘上的 `config.json` 内容**无关**。

**B. 校验结果文件未被替换**
审计链会记录 `winners.csv` 的 `SHA256` 哈希。你可自行计算：
```bash
# Linux/macOS
shasum -a 256 winners.csv
# 或
openssl dgst -sha256 winners.csv
# Windows PowerShell
Get-FileHash winners.csv -Algorithm SHA256
```
对比输出与审计链中最新 `WINNERS_SAVED` 区块的 `winners_hash`。

---

## 对比配置一致性（`--verify-config`）
用于确认**你当前提供的 `config.json`**，是否与**最近一次抽奖**时使用的配置**完全一致**：
```bash
python3 lottery.py --audit-chain audit_chain.jsonl --verify-config config.json
```
该命令会：
1. 先对 `audit_chain.jsonl` 做完整性校验；  
2. 读取最后一次抽奖（最后一个 `draw_id`）的 `GENESIS` 区块内记录的 `config_hash`；  
3. 对当前 `config.json` 做**规范化哈希**（字段排序、参与者按 id 排序、无空格差异影响）；  
4. 比较两者哈希，并输出：
   - `OK: ... matches the recorded hash ...`  
   - 或 `MISMATCH: ... does NOT match ...`

> 这能避免“开奖后改动配置仍能通过 `--verify`”的误解：`--verify` 只保证**链未改**，`--verify-config` 才保证**当前配置与当时一致**。

---

## 复现过去任意一次结果

> 前提：该期的 **`config.json` 保留/公开**（或至少公开其 `SHA256`，期后补充完整内容），以及对应的 `audit_chain.jsonl`。

**步骤：**
1. 获取该期的 `config.json` 与 `audit_chain.jsonl`。  
2. 运行：
   ```bash
   python3 lottery.py --verify --audit-chain audit_chain.jsonl
   python3 lottery.py --audit-chain audit_chain.jsonl --verify-config config.json
   ```
   两者通过后，说明**链未改**且**配置一致**。
3. 使用相同 `config.json` 重新执行抽奖：
   ```bash
   python3 lottery.py --config config.json --winners-out winners_replay.csv --audit-chain audit_chain_replay.jsonl
   ```
4. 对比 `winners_replay.csv` 与原始期 `winners.csv`（或其哈希）。
   - `deterministic`：完全一致；  
   - `system`：脚本会把该次随机种子写进链（`RNG_SEED.seed_int`），回放时用相同配置即可得到相同结果。

---

## 多期活动使用方式
- **同一个** `audit_chain.jsonl` 可以记录**多次抽奖**：每次运行都会追加 3~4 个区块（`GENESIS` / `RNG_SEED` / `DRAW` / `WINNERS_SAVED`）。  
- 建议按期号设置 `manual_seed`，如：`"manual_seed": "Season2-Round5"`。  
- 也可以按期将 `winners` 存不同文件：`winners_2025-10-16.csv`。

---

## 隐私与合规建议
- 若不便公开实名，可在 `participants[*].id` 使用**匿名编号或单向哈希**；公开一份「编号→实名」映射，必要时仅对审计方公开。  
- 公开数据时确保符合隐私法规与平台政策。

---

## 常见问题

**Q1：0 权重的人会中吗？**  
A：会。在正权重不足以填满名额时，会从 0 权重用户中**均匀随机**补齐。此步骤也会记录在审计链中。

**Q2：我用 `deterministic` 模式，为什么每次都是同样结果？**  
A：因为随机种子由「配置+种子」唯一确定，这是**可复现与可审计**的关键。要随机但可复盘，可在 `external_entropy` 中填一个开奖截止后才确定的公共随机值（如区块哈希）。

**Q3：如何确保“开奖后不可抵赖”？**  
A：将**最后区块哈希**公开（Git/推文/群公告/链上 memo 等），别人即可对照核验是否与公开的审计链一致。

**Q4：可以扩展因子吗？**  
A：可以，直接在 `factors` 中增加键值并在参与者 `factors` 序列里使用。未知键会被忽略（按 0 计）。

---

## 示例 `config.sample.json`

> 复制为 `config.json` 后按需修改：

```json
{
  "version": 1,
  "draw": {
    "num_winners": 3,
    "seed_mode": "deterministic",
    "manual_seed": "your-event-id-or-round",
    "external_entropy": "OPTIONAL: e.g., eth block hash of #21938123"
  },
  "factors": {
    "follow": 10,
    "repost": 10,
    "like": 2,
    "reply": 5
  },
  "participants": [
    {"id": "alice", "factors": ["follow", "repost", "like"]},
    {"id": "bob",   "factors": ["reply", "reply", "like"]},
    {"id": "charlie", "factors": []}
  ]
}
```

---

### 开源许可
请在仓库中附上 `LICENSE`（如 MIT/Apache-2.0），以便他人合法复用。
