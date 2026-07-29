# TODO

## 进行中
- 无

## 待办（风险整改 — 2026-07-29）

> 来源文档：`风险整改方案_2026-07-29.md`（项目根目录）

### 阶段一（立即）
- [ ] R01：统一高风险 finding 证据等级为 A+E（修改 cceer_standards.md 第 108 行）
- [ ] R02：对抗验证定量阈值补回（SKILL.md Step 3.7 加 EXPOSED>30%/COVERED<50%）
- [ ] R03：5 份 Prompt 快照重写（依赖 R01/R02 先完成）

### 阶段二（尽快）
- [ ] R04：ProgramIR 闸机接入 program-generator 工作流（新增 Step 4.5）
- [ ] R05：编写 validate-catalog.py（_evidence_catalog.json 结构校验）
- [ ] R06：编写 validate-index.py（index.json 交叉校验）
- [ ] R07：覆盖修复闭环（LLM 自检 + 脚本拦截 + 修复流程，随 R04 联动）

### 阶段三（排期）
- [ ] R08：git pre-commit hook 挂载快照对比脚本（依赖 R03 先完成）
- [ ] R09：端到端回归测试（短期人工抽查 + 中期标准用例积累 + 长期自动化框架）

## 待办（其他）
- P-2026-002 广东长华程序从 v1.0 升级到 v3.0（缺少"取证方式"列，无法自动生成 catalog）
- 部署后做一次完整证据匹配流程端到端测试
- 检查其他已部署项目是否需要运行 update-project.ps1

## 搁置
- 🟢 模型分级（便宜模型 vs 强模型按需使用）— 单人使用 token 成本可控
- 🔵 每个 skill 返回结构化摘要 — ROI 极低

## 阻塞
- 无

## 已完成（2026-07-29）
- ✅ 风险整改方案核验：逐条对照源文件验证 9 项风险诊断准确性
- ✅ 风险整改方案优化：R04 修正（ProgramIR 方案替代 risks_identified.json）、R07 重写（三重屏障）、R08 补齐（有意变更 vs 无意漂移区分）、新增工作量预估和依赖关系图

## 已完成（2026-07-26）
- ✅ 证据集中存储与智能匹配架构设计 + 实现（4 脚本 + 2 文档）
- ✅ PaddleOCR 安装验证（核心识别率 90%+，20分钟/8页，不用于匹配阶段）
- ✅ 项目命名规则固化（project_name = 文件夹名）
- ✅ 证据 v2.0 部署到 P-2026-001 武汉长源 + P-2026-002 广东长华（用户手动完成）
- ✅ 8 次原子化 git 提交

## 已完成（2026-07-22）
- ✅ 四维度系统评估（35 项风险发现）
- ✅ 业务合规整改 12 项（社保标准/公积金/ITGC/派遣舞弊/my-config/OCR）
- ✅ 数据流转审查 27 项 → 22 项确认真实
- ✅ 数据流转整改 22 项（validate-finding 重写/audit_gate 参数/白名单/沙箱/mandatory 检查/schema 补齐/阶段编号/条款数）
- ✅ 2 个项目补登记到 projects-index.json
- ✅ 12 次原子化 git 提交

## 已完成（2026-07-14）
- ✅ 审计技能注册修复
- ✅ program_ir_parser.py MD→ProgramIR 解析器
- ✅ project-init Step 4.6 自动注册
