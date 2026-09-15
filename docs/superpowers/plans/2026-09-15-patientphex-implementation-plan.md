# PatientPheX 2026 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在两张 RTX A6000 上顺序完成 PatientPheX 两个子任务，先产出稳定、合规、可提交的完整基线，再分别提升全文表型识别和患者—表型关联效果。

**Architecture:** 系统由公共数据与评测底座、任务一表型识别与 HPO 归一化、任务二患者—表型关联、最终结果合并四部分组成。任务二可以消费任务一的候选实体，但保留独立补充候选的能力，避免形成不可恢复的级联错误。

**Tech Stack:** Conda、依赖审计后确定的 Python 版本、PyTorch、Hugging Face Transformers/Datasets、PhenoTagger、SapBERT、Qwen3-8B、pytest、JSONL。

**Spec:** 本文件第 1—7 节记录了用户已批准的总体设计、目录、接口和阶段顺序。

## Global Constraints

- 所有代码必须位于 `/mnt/data/wzh/AIcourse/patientphex-2026`。
- 数据、模型、缓存和实验产物位于 `/mnt/data/wzh/AIcourse/patientphex-2026-data`，不得进入 Git。
- `/mnt/data/wzh/AIcourse/patientphex-2026-data/downloads/PatientData/` 是不可修改的原始来源；不得在该目录内改名、覆盖、删除、解压覆盖或清洗文件.
- HPO 固定使用 `v2026-06-23`，只处理 `HP:0000118` 分支。
- 模型参数不得超过赛事 10B 限制；在主办方澄清前按整个推理系统总参数不超过 10B 执行。
- 不使用外部人工标注表型数据集；所有外部资源必须公开可获取并记录来源。
- 训练集和验证集按文章划分，禁止按句子或实体随机拆分同一篇文章。
- 原始全文不得做改变字符长度的清洗；所有 offset 必须能从原文精确回取 text。
- 不并行运行不同 session；同一 session 内可以使用两张 GPU 运行同一阶段的不同数据分片或交叉验证折。
- 每个 session 必须从干净 Git 状态开始，以测试、实验记录、交接文档和 commit 结束。

---

## 1. 服务器目录

### 1.1 Git 仓库

```text
/mnt/data/wzh/AIcourse/patientphex-2026/
├── README.md
├── PROJECT_STATUS.md
├── .gitignore
├── configs/
│   ├── common/
│   ├── task1/
│   └── task2/
├── environments/
├── src/patientphex/
│   ├── common/
│   ├── task1/
│   └── task2/
├── scripts/
├── tests/
├── third_party/
└── docs/
    ├── data/
    ├── experiments/
    ├── handoffs/
    ├── superpowers/plans/
    └── resources.md
```

### 1.2 数据与实验资产

```text
/mnt/data/wzh/AIcourse/patientphex-2026-data/
├── downloads/
├── raw/
├── processed/
├── ontology/
├── models/
│   ├── pretrained/
│   └── checkpoints/
├── cache/
│   ├── huggingface/
│   └── torch/
├── runs/
└── submissions/
```

`downloads/PatientData/` 保存用户下载并解压后的原始文件，作为只读来源；S0
完成校验后，将 `downloads/PatientData/hp.obo` 复制到
`ontology/hp-2026-06-23.obo`，后续代码只从该固定路径读取 HPO。

### 1.3 环境变量

```bash
export PATIENTPHEX_REPO=/mnt/data/wzh/AIcourse/patientphex-2026
export PATIENTPHEX_DATA_ROOT=/mnt/data/wzh/AIcourse/patientphex-2026-data
export HF_HOME=/mnt/data/wzh/AIcourse/patientphex-2026-data/cache/huggingface
```

---

## 2. 固定数据接口

后续 session 只能通过以下约定交换数据：

```text
processed/documents.jsonl
processed/folds.json
runs/<run_id>/task1_entities.jsonl
runs/<run_id>/task2_associations.jsonl
submissions/<run_id>.jsonl
```

- `documents.jsonl`：保留官方字段、原始 section 文本和全局 offset。
- `folds.json`：固定文章级五折划分及随机种子。
- `task1_entities.jsonl`：以 `pmc_id` 为主键，仅包含任务一实体预测。
- `task2_associations.jsonl`：以 `pmc_id` 为主键，仅包含任务二患者关联预测。
- `submissions/<run_id>.jsonl`：合并后的最终提交文件。

---

## 3. 时间与里程碑

| 时间 | Session | 交付物 |
|---|---|---|
| 9月15—16日 | S0 环境与数据底座 | 目录、Git、数据审计、Conda 兼容性结论 |
| 9月17日 | S1 公共解析与评测 | 数据解析器、四项指标、提交验证器 |
| 9月18—19日 | S2 任务一基线 | PhenoTagger/词典基线和任务一预测 |
| 9月20—21日 | S3 任务二基线 | 患者别名和局部关联基线 |
| 9月22日 | S4 联合基线 | 第一份完整、合法、可复现的提交 |
| 9月23—27日 | S5/S6 增强 | 任务一 AutoPCR-lite；任务二关系增强 |
| 9月28日—10月1日 | S7 B榜 | 模型冻结、B榜推理和历史最优提交 |
| 10月2—15日 | S8 论文与复现 | 五折结果、消融、技术论文和材料 |
| 10月16—20日 | S9 后续完善 | 不影响榜单的工程与研究完善 |

官方当前安排为 A 榜 9 月 27 日截止、B 榜 10 月 1 日截止、论文 10 月 15 日截止。若主办方更新日程，以最新公告为准。

---

## 4. Session S0：环境与数据底座

**Files:**

- Create: `README.md`
- Create: `PROJECT_STATUS.md`
- Create: `.gitignore`
- Create: `environments/compatibility.md`
- Create: `docs/data/data-audit.md`
- Create: `docs/resources.md`
- Create: `scripts/check_environment.py`
- Create: `tests/test_environment_contract.py`

**Interfaces:**

- Consumes: 用户上传到只读目录 `downloads/PatientData/` 的官方原始文件。
- Produces: 可读的原始数据、HPO v2026-06-23、依赖兼容性结论、确定的 Conda 环境方案。

- [ ] 建立第 1 节中的代码和数据目录。
- [ ] 初始化服务器本地 Git 仓库，主分支命名为 `main`。
- [ ] 计算 `downloads/PatientData/` 中原始文件的 SHA256，并把文件名、大小、校验值写入 `docs/data/data-audit.md`；完成后将该目录及其文件设为只读来源。
- [ ] 检查原始文件内容并复制到 `raw/official/`（不得修改原始来源）；将 `downloads/PatientData/hp.obo` 复制并固定为 `ontology/hp-2026-06-23.obo`，核对复制前后 SHA256 一致。
- [ ] 统计文章、患者、实体和关联数量，并与官方说明核对。
- [ ] 下载 HPO v2026-06-23，记录原始 URL、版本和校验值。
- [ ] 分别验证 PhenoTagger、PyTorch/Hugging Face、SapBERT 和 Qwen3-8B 的 Python/CUDA 兼容性。
- [ ] 优先建立 `patientphex-main`；仅当依赖冲突被复现后建立 `patientphex-phenotagger`。
- [ ] 导出 Conda YAML 和 explicit package list。
- [ ] 运行 `pytest -q tests/test_environment_contract.py`。
- [ ] 更新 `docs/handoffs/S0-foundation.md` 并提交 `chore: initialize project foundation`。

**Acceptance:**

- 原始数据完整且校验值已记录。
- HPO 版本准确。
- 两张 A6000 均可被 PyTorch 识别。
- Python 版本由真实依赖测试决定，而不是预先猜测。

---

## 5. Session S1：公共解析、评测与提交验证

**Files:**

- Create: `src/patientphex/common/schema.py`
- Create: `src/patientphex/common/io.py`
- Create: `src/patientphex/common/offsets.py`
- Create: `src/patientphex/common/hpo.py`
- Create: `src/patientphex/common/metrics.py`
- Create: `src/patientphex/common/validation.py`
- Create: `src/patientphex/common/merge.py`
- Create: `tests/common/`
- Create: `scripts/prepare_data.py`
- Create: `scripts/evaluate.py`
- Create: `scripts/validate_submission.py`

**Interfaces:**

- Consumes: `raw/official/` 和固定文件 `ontology/hp-2026-06-23.obo`。
- Produces: `processed/documents.jsonl`、`processed/folds.json`、统一评测和提交验证接口。

- [ ] 为官方 JSONL 样例编写解析失败测试。
- [ ] 实现逐行 JSONL 读取和字段校验。
- [ ] 为跨 section 全局 offset 编写回取测试。
- [ ] 实现原文、section 和全局字符位置映射。
- [ ] 为 HPO 分支过滤、名称和同义词索引编写测试。
- [ ] 实现 HPO v2026-06-23 加载器。
- [ ] 用手工构造样例编写 Mention-F1、Document-F1、Micro-F1、Macro-F1 测试。
- [ ] 实现四项指标和总分计算。
- [ ] 实现任务一、任务二结果合并器。
- [ ] 实现 UTF-8、pmc_id、offset、HPO ID、patient_id 和重复结果验证。
- [ ] 生成固定文章级五折划分。
- [ ] 运行 `pytest -q tests/common`。
- [ ] 更新 `docs/handoffs/S1-common.md` 并提交 `feat: add common data and evaluation pipeline`。

**Acceptance:**

- 所有训练实体满足 `source[offset:offset+length] == text`。
- 四项指标通过可人工核算的小样例测试。
- 空预测和正常预测均能生成结构合法的 JSONL。

---

## 6. Session S2：任务一可提交基线

**Files:**

- Create: `src/patientphex/task1/dictionary.py`
- Create: `src/patientphex/task1/phenotagger.py`
- Create: `src/patientphex/task1/candidates.py`
- Create: `src/patientphex/task1/normalization.py`
- Create: `src/patientphex/task1/postprocess.py`
- Create: `src/patientphex/task1/pipeline.py`
- Create: `configs/task1/baseline.yaml`
- Create: `tests/task1/`
- Create: `scripts/run_task1.py`

**Interfaces:**

- Consumes: `processed/documents.jsonl`、冻结 HPO、PhenoTagger 输出。
- Produces: `runs/<run_id>/task1_entities.jsonl`。

- [ ] 用训练样例为词典匹配、重叠、否定、复合表型和精确 offset 编写测试。
- [ ] 从冻结 HPO 构建名称与同义词词典。
- [ ] 配置 PhenoTagger 使用比赛 HPO 版本。
- [ ] 合并词典和 PhenoTagger 候选。
- [ ] 完全匹配时直接映射 HPO；无可靠映射时按规则处理 `-1`。
- [ ] 实现重复、重叠、否定和简单复合表型后处理。
- [ ] 在文章级固定划分上计算 Mention-F1 和 Document-F1。
- [ ] 运行任务一提交验证器。
- [ ] 记录运行配置、指标、错误样例和耗时。
- [ ] 运行 `pytest -q tests/task1`。
- [ ] 更新 `docs/handoffs/S2-task1-baseline.md` 并提交 `feat(task1): add reproducible baseline`。

**Acceptance:**

- 任务一预测文件可由单条命令生成。
- 每个预测实体均能从原文精确回取。
- Mention-F1 和 Document-F1 均为非零，并记录可复现基线。

---

## 7. Session S3：任务二可提交基线

**Files:**

- Create: `src/patientphex/task2/patients.py`
- Create: `src/patientphex/task2/aliases.py`
- Create: `src/patientphex/task2/context.py`
- Create: `src/patientphex/task2/rules.py`
- Create: `src/patientphex/task2/aggregate.py`
- Create: `src/patientphex/task2/pipeline.py`
- Create: `configs/task2/baseline.yaml`
- Create: `tests/task2/`
- Create: `scripts/run_task2.py`

**Interfaces:**

- Consumes: 原始全文、官方患者及其 mention、section 映射、任务一候选。
- Produces: `runs/<run_id>/task2_associations.jsonl`。

- [ ] 为 proband、case、家系编号、年龄性别别名和多患者段落编写测试。
- [ ] 建立 patient_id 与明确 mention 的映射。
- [ ] 实现文章内简单患者别名扩展。
- [ ] 实现句子、段落和病例小节的活跃患者状态。
- [ ] 生成患者—表型候选对。
- [ ] 使用同句、同段、距离、否定和亲属线索进行规则打分。
- [ ] 聚合并去重患者级 HPO 集合。
- [ ] 在文章级固定划分上计算 Micro-F1 和 Macro-F1。
- [ ] 与“把全文所有 HPO 分给每位患者”的弱基线比较。
- [ ] 运行 `pytest -q tests/task2`。
- [ ] 更新 `docs/handoffs/S3-task2-baseline.md` 并提交 `feat(task2): add patient association baseline`。

**Acceptance:**

- 所有 patient_id 均来自官方输入。
- 每位患者只有一个去重后的表型集合。
- Micro-F1 和 Macro-F1 均优于弱基线。

---

## 8. Session S4：第一份完整提交

**Files:**

- Create: `configs/common/submission-baseline.yaml`
- Create: `scripts/run_full_pipeline.py`
- Create: `docs/experiments/baseline-submission.md`

**Interfaces:**

- Consumes: S2 任务一预测和 S3 任务二预测。
- Produces: `submissions/<run_id>.jsonl`。

- [ ] 合并 entities 和 association。
- [ ] 验证文献数量、pmc_id、UTF-8、offset、HPO ID 和 patient_id。
- [ ] 从固定 commit 重新运行一次完整流水线。
- [ ] 比较两次输出 SHA256，确认确定性。
- [ ] 记录提交文件、配置、commit、模型版本和时间。
- [ ] 更新 `docs/handoffs/S4-submission.md` 并提交 `feat: add end-to-end baseline submission`。

**Acceptance:**

- 完整提交通过本地验证器。
- 从干净环境可一键复现相同文件。
- 第一份 A 榜结果最迟在 9 月 23—24 日提交。

---

## 9. Session S5：任务一增强

**Files:**

- Create: `src/patientphex/task1/neural_ner.py`
- Create: `src/patientphex/task1/retrieval.py`
- Create: `src/patientphex/task1/reranker.py`
- Create: `configs/task1/autopcr_lite.yaml`
- Create: `scripts/train_task1_ner.py`
- Create: `scripts/build_hpo_index.py`
- Create: `docs/experiments/task1-ablation.md`

**Interfaces:**

- Consumes: S2 候选接口和 S1 HPO 索引。
- Produces: 改进后的任务一预测，输出格式保持不变。

- [ ] 微调 BiomedBERT/PubMedBERT 序列标注模型。
- [ ] 合并词典、PhenoTagger 和神经模型候选。
- [ ] 使用 SapBERT 构建 HPO Top-K 检索。
- [ ] 高置信度候选直接接受，低置信度候选进入受约束重排。
- [ ] 只允许重排器从检索候选中选择 HPO。
- [ ] 增加并列结构、缩写、否定和边界修正规则。
- [ ] 完成文章级五折验证和消融实验。
- [ ] 仅当 `(Mention-F1 + Document-F1) / 2` 稳定优于 S2 时替换基线。
- [ ] 更新交接文档并提交 `feat(task1): add retrieval-augmented normalization`。

---

## 10. Session S6：任务二增强

**Files:**

- Create: `src/patientphex/task2/patient_graph.py`
- Create: `src/patientphex/task2/pair_features.py`
- Create: `src/patientphex/task2/relation_model.py`
- Create: `src/patientphex/task2/llm_reranker.py`
- Create: `src/patientphex/task2/direct_branch.py`
- Create: `configs/task2/enhanced.yaml`
- Create: `scripts/train_task2_relation.py`
- Create: `docs/experiments/task2-ablation.md`

**Interfaces:**

- Consumes: S3 规则候选、S5 表型候选和局部证据窗口。
- Produces: 改进后的患者级 HPO 集合，输出格式保持不变。

- [ ] 建立患者别名图和家属关系图。
- [ ] 增强小节、段落和跨句活跃患者传播。
- [ ] 构造患者—表型对的距离、依存、章节、否定和经历者特征。
- [ ] 使用规则银标或多实例学习训练关系分类器。
- [ ] 用 Qwen3-8B 对疑难关系做受约束选择，不允许自由生成 patient_id。
- [ ] 加入不依赖任务一最终输出的患者→HPO 辅助分支。
- [ ] 完成文章级五折验证和消融实验。
- [ ] 仅当 `(Micro-F1 + Macro-F1) / 2` 稳定优于 S3 时替换基线。
- [ ] 更新交接文档并提交 `feat(task2): add patient graph and relation scoring`。

---

## 11. Session S7：B榜冻结与提交

- [ ] 在 9 月 27 日前冻结代码、模型、阈值和候选配置。
- [ ] 下载 B 榜数据后先执行数据完整性和 schema 检查。
- [ ] 生成稳定版与增强版两个候选提交。
- [ ] 对每个提交保存 SHA256、commit、配置和模型清单。
- [ ] 每日不超过官方规定的 3 次 B 榜提交。
- [ ] 保留历史最优版本，不因后续低分提交覆盖可复现材料。
- [ ] 为最终版本创建 Git tag。

---

## 12. GPU 使用规则

- GPU 0 默认用于当前阶段的主训练或主推理。
- GPU 1 用于同一阶段的另一折交叉验证、消融或推理分片。
- 不允许两个不同 session 同时工作或同时修改仓库。
- Qwen3-8B 优先单卡 BF16 推理。
- 只有经过单卡吞吐和显存测试后才启用双卡 DDP。
- 每次运行必须记录 `CUDA_VISIBLE_DEVICES`、随机种子、配置、commit、日志和 checkpoint。

---

## 13. Session 交接规则

每个 session 开始时运行：

```bash
git status
git log -5 --oneline
pytest -q
```

如果 Git 状态不干净或测试失败，先阅读上一份交接文档，不得直接继续开发。

每个 session 结束时更新：

```text
PROJECT_STATUS.md
docs/handoffs/SXX-名称.md
```

交接文档必须包含：

- 开始和结束 commit；
- 完成与未完成内容；
- 新增和修改文件；
- 完整运行命令；
- 指标、耗时和 GPU；
- 已知错误与失败实验；
- 下一 session 的输入文件和验收标准。

推荐 commit：

```text
chore: initialize project foundation
feat(eval): add official metrics and validation
feat(task1): add reproducible baseline
feat(task2): add patient association baseline
exp(task1): add sapbert reranking
fix(offset): preserve exact document offsets
```

---

## 14. 用户数据上传步骤

1. 登录天池并下载训练集与 A 榜测试集。
2. 保留原始文件，不在本地修改或重新打包。
3. 在 Windows PowerShell 使用实际文件路径运行：

```powershell
scp "C:\实际下载目录\实际文件名" A6000-hitsz:/mnt/data/wzh/AIcourse/patientphex-2026-data/downloads/PatientData/
```

4. 上传完成后通知 S0 session 文件名；由 S0 负责校验并将原始来源目录设为只读。

---

## 15. 完成定义

项目完成至少需要满足：

- 从干净 Conda 环境可运行完整流水线。
- 任务一和任务二均有基线及离线指标。
- 最终提交通过本地 schema、offset、HPO 和 patient 校验。
- 所有外部资源和许可证可追溯。
- 最终模型符合 10B 和外部数据限制。
- 最佳提交可由 Git tag、配置和模型清单复现。
