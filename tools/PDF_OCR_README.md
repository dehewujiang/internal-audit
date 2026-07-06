# PDF OCR 解析工具使用说明

## 工具文件

- **路径**: `tools/pdf_ocr_extractor.py`
- **OCR引擎**: EasyOCR（推荐用于中文制度文件）

---

## EasyOCR优势

| 特性 | EasyOCR | Tesseract |
|------|---------|-----------|
| **中文准确率** | ⭐⭐⭐⭐⭐ 深度学习模型，专业术语识别更好 | ⭐⭐⭐ 传统OCR，中文版面复杂时效果差 |
| **安装难度** | ⭐⭐⭐⭐⭐ `pip install easyocr` 即可 | ⭐⭐ 需额外安装Tesseract系统级软件 |
| **表格/多栏** | ⭐⭐⭐⭐⭐ 深度学习保留排版更好 | ⭐⭐ 需手动配置版面分析参数 |
| **离线运行** | ⭐⭐⭐⭐ 首次下载模型后长期可用 | ⭐⭐⭐ 需安装语言包 |

---

## 依赖安装

### 1. Python包

```bash
pip install pdf2image pillow easyocr
```

**首次运行提示**：
- EasyOCR会自动下载`ch_sim`模型（约100MB），需网络连接
- 模型保存在用户目录`~EasyOCR`，下载后重复使用

### 2. 系统工具

仅需要 **Poppler**（用于PDF转图片）：

#### Windows
1. 下载: https://github.com/oschwartz10612/poppler-windows/releases/
2. 解压到 `C:\poppler`
3. 将 `C:\poppler\Library\bin` 加入系统PATH

#### Linux
```bash
sudo apt-get install poppler-utils
```

#### Mac
```bash
brew install poppler
```

### 3. 验证安装

```bash
pdftoppm -v  # 验证Poppler
python -c "import easyocr; print('EasyOCR OK')"  # 验证Python包
```

---

## 使用方法

### 单文件处理

```bash
# 默认语言：简体中文
python tools/pdf_ocr_extractor.py "internal-audit-workspace/documents/NPM001.pdf"

# 指定输出目录
python tools/pdf_ocr_extractor.py "NPM001.pdf" "./output"

# 中英文混合
python tools/pdf_ocr_extractor.py "NPM001.pdf" "./output" "ch_sim+en"

# 繁体中文
python tools/pdf_ocr_extractor.py "NPM001.pdf" "./output" "ch_tra"
```

### 批量处理（推荐）

```bash
# 处理整个制度文件夹
python tools/pdf_ocr_extractor.py --batch "internal-audit-workspace/documents" "ch_sim"
```

---

## 语言代码参考

| 代码 | 语言 | 适用场景 |
|------|------|----------|
| `ch_sim` | 简体中文 | **默认推荐**，国内制度文件 |
| `ch_tra` | 繁体中文 | 港台地区文档 |
| `en` | 英文 | 纯英文文档 |
| `ch_sim+en` | 简中+英文 | 中英文混合文档 |

---

## 输出文件

工具会生成两个文件：

| 文件 | 说明 | 用途 |
|------|------|------|
| `{文件名}_ocr.txt` | 纯文本格式，按页分离 | **推荐**，直接供Claude阅读分析 |
| `{文件名}_ocr.json` | JSON格式，包含元数据 | 程序化读取，保留OCR块信息 |

---

## 当前项目处理建议

由于7份PDF为扫描件（NPM001/007/011/015/019, NXM003x2）：

```bash
# 一次性处理所有扫描件
python tools/pdf_ocr_extractor.py --batch "internal-audit-workspace/documents" "ch_sim"
```

处理后：
1. 将生成的 `{文件名}_ocr.txt` 提供给Claude
2. 重新执行完整的制度分析（8份文档）
3. 更新审计程序（基于完整制度体系）

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| "缺少Poppler" | pdftoppm未安装或未添加到PATH | 按上方步骤安装Poppler |
| "模型下载失败" | 首次使用需要联网下载模型 | 检查网络连接，重试会自动下载 |
| 识别为空 | PDF是纯图片但分辨率太低 | 尝试提高DPI（改代码中dpi参数） |
| 文字排版混乱 | 多栏/表格布局复杂 | EasyOCR已优化，比Tesseract更好 |

---

## 技术对比（为什么选择EasyOCR）

**中文制度文件特点**：
- 大量专业术语（审批、核销、呆滞料等）
- 表格、多栏排版常见
- 盖章、手写批注干扰

**Tesseract局限**：
- `chi_sim`训练数据陈旧，对新术语识别差
- 版面分析需手动配置，表格常识别为连续文本
- 复杂背景下准确率下降明显

**EasyOCR优势**：
- 基于PyTorch深度学习，持续更新模型
- 内置版面分析，自动识别文本区域
- 对扫描件质量容忍度更高
