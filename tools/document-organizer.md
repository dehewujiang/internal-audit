# document-organizer

## 能力
- 读取并分析制度文件（PDF/Word/MD/TXT，含扫描件OCR文本）
- 提取审批权限控制、职责分离控制、定期检查控制、文档记录控制
- 识别流程断裂点、权限集中点、监督盲区、信息不对称点
- 跨文件交叉验证，检测制度冲突
- 对照 reference_framework 识别制度缺失模块（完整性检查）
- 输出为 JSON + Markdown 双格式

## 限制
- 输入文件必须已转为可读文本（图片/扫描件的OCR由中央大脑内置处理）
- 不能对非中文文档进行准确分析
- 单次分析建议不超过 15 个文件

## 输入
- documents/: 制度文件目录
- about-me.md: 公司背景（可选）
- topic.json::reference_framework: 完整制度框架定义（完整性检查用，由宪法强制）

## 输出
- policy-analyses/{doc_name}.json
- design-assessments/: 设计观察
- signals/: 制度缺失项（由完整性检查触发），每项含缺失模块名称、缺失影响描述、对标参照（如有）

## 授权
level_0
