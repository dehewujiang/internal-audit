# 内部审计平台数据流总图

```
        ┌───────────────────────────────────────────────────────┐
        │              中央大脑（胶水 + 决策 + 记忆）              │
        │  读状态 → 判断 → 调 skill / 跑脚本 → 写回状态            │
        └───────────────────────┬───────────────────────────────┘
                                │ 每次读写
                                ▼
        ┌───────────────────────────────────────────────────────┐
        │  current-audit.json（唯一状态文件）                      │
        │  status 阶段 · audit_state 状态 · audit_trail 轨迹       │
        │  + 最近 20 份快照（可回滚）                               │
        └───────────────────────────────────────────────────────┘


【P0 初始化 / phase_0_init】  project-init / topic-wizard
   产出：current-audit.json · topic.json · about-me.md · my-config.md
                    │
            phase_gate check/advance （流程闸机）
                    ▼
【P1 制度分析 / phase_1_document_analysis】  document-organizer
   输入：制度文件（扫描件 → OCR 提取）
   产出：policy-analyses/*.json ＋ design-assessments/*.json（设计观察）
   校验：validate-policy-analysis.py          ← 质量闸机
   硬底线：check_mandatory_coverage.py（制度空白 → 信号池，最低"高"风险）
                    │
            phase_gate check/advance
                    ▼
【P1.5 访谈 / phase_1_5_interview】  audit-interview-designer
   输入：design-assessments ＋ about-me ＋ 历史发现
   产出：interview-materials/（Excel 问卷 ＋ 资料需求清单）
   回填：访谈结果 → design-assessments/（追加同一文件）
   校验：validate-interview.py                ← 质量闸机
                    │
            phase_gate check/advance
                    ▼
【P2 程序生成 / phase_2_program_generation】  program-generator
   输入：policy-analyses ＋ design-assessments(风险线索) ＋ 公司背景/配置
   产出：audit-programs/*.md（8 张表，含设计理由/测试目的两列）
   闸机：ProgramIR 解析 → validate-program.py --ir --strict
        （风险覆盖率 <80% 拦截；增量模式 S 序列、-C 勘误）
                    │
            phase_gate check/advance
                    ▼
【P3 执行取证 / phase_3_execution】  execution-assistant
   输入：audit-programs ＋ design-assessments ＋ 证据（用户提供）
   证据：_evidence_catalog.json ＋ _files/（v2.0 集中存储，多程序共用）
   工具：data_executor（数据沙箱）· OCR 识别
   产出：findings/*.json ＋ findings/index.json
   校验：validate-catalog.py（取证前）· validate-finding.py · validate-index.py
   可选：finding-debate（业务攻防 → 回写 finding）
                    │
            phase_gate check/advance
                    ▼
【P4 报告 / phase_4_report】  report-generator
   输入：findings ＋ audit-programs ＋ design-assessments ＋ 公司背景
   产出：reports/（结构化报告 ＋ Excel 汇总）
   校验：validate-report.py                   ← 质量闸机


         ┌─ 贯穿性机制 ─────────────────────────────────┐
         │ 调度闸机  audit_gate（LLM 推理前后强制校验）     │
         │ 授权闸机  phase_gate tool-check（脚本白名单）   │
         │ 注册表    projects-index.json（多项目并行）     │
         │ 来源声明  每次输出标注"Skill 生成/脚本输出"      │
         └──────────────────────────────────────────────┘
```

## 断点观察

1. 推理轨迹无落点：audit_trail 只记状态变更（推进/回滚/强制放行），"为什么选这个程序、为什么定高风险"无承载 → C6 试点补 decision 事件
2. design-assessments 被 P1.5/P2/P3/P4 全量读 4 次，无裁剪 → C7 补最小必要上下文
3. 证据缺失闭环：P3 证据缺失按宪法 #9 应进信号池，链路待确认 → F1 验证时核对

## 图例说明

- **中央大脑**：系统调度核心，负责读状态 → 判断 → 调用 Skill / 运行脚本 → 写回状态。
- **current-audit.json**：唯一状态文件，记录当前阶段（status）、审计状态（audit_state）、审计轨迹（audit_trail）及最近 20 份快照（支持回滚）。
- **P0–P4 阶段**：六阶段流水线（初始化 → 制度分析 → 访谈 → 程序生成 → 执行取证 → 报告），每个阶段由一个 Skill 承接，阶段间经 `phase_gate` 流程闸机校验后推进。
- **质量闸机**：`validate-*.py` 系列脚本，阶段产出必须通过校验才能进入下一阶段。
- **贯穿性机制**：作用于全流程的横向机制（调度闸机、授权闸机、项目注册表、来源声明）。
- **断点观察**：当前架构中已识别但尚未闭环的薄弱点，对应后续改进事项（C6 / C7 / F1）。
