---
name: geb-bootstrap
description: GEB 文档体系冷启动播种。当项目缺少 AGENTS.md 或需要初始化三层文档结构时调用。会扫描目录、推断职责、播下 L1/L2/L3 并建立 symlink。
---

# GEB 冷启动播种流程

## Phase 1：侦察

- 检查 /AGENTS.md 是否存在；存在则读取理解，不存在则准备播种。
- 扫描目录结构，识别模块边界，规划播种路径。
- 分析 package.json / go.mod / requirements.txt 获取技术栈。

## Phase 2：播种

- L1 缺失 → 播下 L1（全局地图：目录 / 配置 / 法则）。
- L2 缺失 → 列举文件 + 读前 50 行 → 推断职责 → 播下 L2（成员清单 + 父级链接）。每个 L2 开头声明："一旦我所属的文件夹有所变化，请务必更新我"。
- L3 缺失 → 分析 import / export → 推断位置 → 播下 L3 头部注释（INPUT / OUTPUT / POS）。
- 创建 symlink：AGENTS.md → AGENTS.md（保证不同 Agent 工具发现同一份文档）。

## Phase 3：生根

- 在 L1 顶部记录"文档播种日期"与"维护者"。
- 进入正常工作流，每次修改后回环检查维持同构。
- 此后每次代码变更，都是在浇灌这片文档森林。