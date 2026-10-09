# 设计观察验证与升级（Step 0）

> SKILL.md Step 0 的完整细节。正文只留原则，干活时读这里。

1. 读取 `internal-audit-workspace/audit-programs/` 中最新的审计程序文档
2. 提取所有审计程序清单（风险编号、程序名称、取数来源、测试步骤）
3. 初始化执行进度追踪
4. **读取 design-assessments/ 中 `status="pending"` 的设计观察**（不限来源，如存在）
   - 记录待验证的设计观察清单
   - 在执行过程中逐项验证

**设计观察→发现的升级路径**：

```
Phase 1：document-organizer → design-assessments/（制度文本分析，JSON 格式）
    ↑↓
Phase 1.5：interview-designer 模式B → design-assessments/（访谈回填，追加到同一JSON文件）
    ↓
Phase 4：审计执行阶段，针对每个设计观察设计验证程序
    ↓ 验证通过（实地证据证实设计缺陷确实导致问题）
桌子 left[] 存储经证实的发现，origin="design"，关联 design_observation_id
    ↓ 验证不通过（设计虽有缺陷但未造成实际影响）
标记"设计观察不成立"，保留在design-assessments/中，不上桌
```

**NOTE：`design-assessments/` 中的设计观察可能来自两个来源**：
| 来源 | source 字段 | 特征 |
|------|-----------|------|
| Phase 1 制度分析 | `"document-organizer"` | 基于制度文本，含 source_doc/source_section |
| Phase 1.5 访谈回填 | `"interview"` | 含 source_role/source_id/interview_snippet，可能含 contradiction |

interview 来源的验证需额外处理（详见 document-organizer/references/design-observation-format.md）：

| 条件 | 验证要求 |
|------|---------|
| `source_role="操作员"` | 必须 ≥2 个独立信源交叉验证 |
| `contradiction` 非空 | 必须包含矛盾排查步骤 |
| interview 线索升级为 finding | interview_snippet 作为 evidence 条目写入 |

**重要原则**：
- 设计观察（design observation）≠ 审计发现（finding）
- 设计观察是**假设**，基于制度文本分析得出
- 审计发现是**结论**，基于实地证据验证得出
- 只有经过实地验证的设计观察才能升级为finding
- finding JSON中必须标注 `origin` 字段（"design" 或 "execution"）

**输出**：
```
审计程序加载完成。
审计主题：存货管理审计
程序总数：15项
当前进度：0/15

请按顺序执行程序，或输入"跳转到程序X"。
```
