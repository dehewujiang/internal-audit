# 搬家说明书：从"写本子再抄"改成"直接写桌子"

> 大白话：以前每个技能查出东西，先写自己的本子，再用sweep抄到桌子上。
> 以后查出东西，直接写桌子，本子变成"底稿"（记过程），自动生成。

## 要改哪几间房

| 房间（技能） | 以前怎么写 | 以后怎么写 |
|---|---|---|
| 看制度（document-organizer） | 写 policy-analyses/*.json，再sweep | 直接写桌子 + 生成底稿 |
| 问话（audit-interview-designer） | 写 design-assessments/*.json，再sweep | 直接写桌子 + 生成底稿 |
| 检查单（program-generator） | 写 audit-programs/*.md，再sweep | 程序照旧出文档，推演风险直接写桌子 |
| 执行取证（execution-assistant） | 写 findings/*.json，再sweep | 直接写桌子 + 生成底稿 |
| 吵架（finding-debate） | 改 findings/*.json | 直接改桌子（set-slot） |
| 报告（report-generator） | 读 findings/*.json | 读桌子 |

## 每间房具体改什么

### 1. 看制度（document-organizer）

**以前的产出步骤：**
```
Step X: 分析制度文件
Step Y: 写入 policy-analyses/xxx.json（控制点、风险点、缺口、冲突）
Step Z: 运行 sweep 抄到桌子
```

**以后的产出步骤：**
```
Step X: 分析制度文件
Step Y: 把结论直接写桌子（add-line），每条带来源标记
Step Z: 把分析过程写底稿（working-papers/xxx.md），记"为什么这么判断"
        （不再需要 sweep）
```

**具体写桌子的对照：**
- 控制缺口 已确认 → add-line 到"确定的毛病"格
- 控制缺口 待确认 → add-line 到"说不清的信号"格
- 制度冲突 → add-line 到"确定的毛病"格
- 风险点 → add-line 到"说不清的信号"格
- 设计观察 pending → add-line 到"说不清的信号"格

### 2. 问话（audit-interview-designer）

**以前：** 写 design-assessments/*.json，再sweep
**以后：** 风险线索直接写桌子，问卷照旧出Excel

### 3. 检查单（program-generator）

**以前：** 写 audit-programs/*.md，推演风险sweep到桌子
**以后：** 程序照旧出文档（8张表是工作说明，桌子装不下），推演风险直接写桌子

### 4. 执行取证（execution-assistant）

**以前的产出步骤：**
```
Step X: 分析证据
Step Y: 写入 findings/F-2026-xxx.json
Step Z: 运行 sweep --finding F-xxx 抄到桌子
```

**以后的产出步骤：**
```
Step X: 分析证据
Step Y: 把结论直接写桌子（add-line），带来源和证据条
Step Z: 把分析过程写底稿（working-papers/F-2026-xxx.md）
        （不再需要 sweep）
```

### 5. 吵架（finding-debate）

**以前：** 改 findings/*.json 里的结论
**以后：** 直接改桌子上的字（set-slot，改前自动拍照）

### 6. 报告（report-generator）

**以前：** 读 findings/*.json + audit-programs/*.md
**以后：** 读桌子 + 抽屉里的程序文档

## 新旧对照（一眼看出来）

```
以前：
  技能 → 写本子 → sweep抄桌子 → 报告
           ↑
         ingested记着抄了啥

以后：
  技能 → 直接写桌子 → 报告
           ↓
       自动生成底稿（记过程）
```

## 注意事项

1. **照旧出文档的**：审计程序、访谈问卷、报告——这些是工具和成品，不是发现，桌子只记"在哪"
2. **不再单独出文档的**：控制缺口、风险点、问题单结论——这些直接写桌子
3. **底稿自动生成**：分析过程（为什么这么判断）写到 working-papers/，不用手工维护
4. **老项目搬家**：旧的 policy-analyses/findings 文件可以用 import 一次性搬到桌子，之后就只写桌子了
