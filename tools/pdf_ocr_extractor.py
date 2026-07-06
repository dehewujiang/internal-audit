#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF扫描件OCR解析工具（EasyOCR版本）
将PDF图片转换为可提取的文本

依赖安装:
    pip install pdf2image pillow easyocr

系统依赖:
    Windows: 安装Poppler https://github.com/oschwartz10612/poppler-windows/releases/
    Linux: sudo apt-get install poppler-utils
    Mac: brew install poppler

首次使用EasyOCR时会自动下载模型（约100MB），需联网

使用方法:
    python pdf_ocr_extractor.py <pdf文件路径> [输出目录] [语言]

示例:
    python pdf_ocr_extractor.py "NPM001.pdf" "./output" "ch_sim"
    python pdf_ocr_extractor.py --batch "./policies" "ch_sim"

语言代码参考:
    ch_sim  - 简体中文
    ch_tra  - 繁体中文
    en      - 英文
    ch_sim+en - 中英文混合
"""

import os
import sys
import json
from pathlib import Path


def check_dependencies():
    """检查必要的依赖是否已安装"""
    missing = []

    try:
        import pdf2image
    except ImportError:
        missing.append("pdf2image")

    try:
        import easyocr
    except ImportError:
        missing.append("easyocr")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    if missing:
        print("错误: 缺少以下Python包:")
        for pkg in missing:
            print(f"  - {pkg}")
        print(f"\n请运行: pip install {' '.join(missing)}")
        print("\n注意: 首次安装easyocr后，首次使用时会自动下载模型文件（约100MB）")
        return False

    return True


def check_system_dependencies():
    """检查系统级依赖"""
    import shutil

    if not shutil.which("pdftoppm"):
        print("错误: 缺少Poppler工具")
        print("  Windows: 下载 https://github.com/oschwartz10612/poppler-windows/releases/")
        print("  Linux: sudo apt-get install poppler-utils")
        print("  Mac: brew install poppler")
        print("\n安装后将 bin 目录添加到系统PATH")
        return False

    return True


def detect_table_regions(ocr_result, img_height, img_width):
    """
    检测可能的表格区域
    表格特征：文本块在行和列上呈规律性分布
    """
    if len(ocr_result) < 4:
        return []
    
    tables = []
    # 简单的表格检测：文本块呈网格状分布
    y_positions = []
    for bbox, text, conf in ocr_result:
        if conf > 0.3:
            # bbox格式: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            y_center = (bbox[0][1] + bbox[2][1]) / 2
            y_positions.append((y_center, bbox, text))
    
    # 按Y坐标排序，查找行
    y_positions.sort(key=lambda x: x[0])
    
    # 检测行（Y坐标接近的文本块）
    rows = []
    current_row = []
    last_y = None
    y_threshold = img_height * 0.03  # 3%高度作为行间距
    
    for y, bbox, text in y_positions:
        if last_y is None or abs(y - last_y) < y_threshold:
            current_row.append((y, bbox, text))
        else:
            if len(current_row) >= 3:  # 一行至少有3个文本块才可能是表格
                rows.append(current_row)
            current_row = [(y, bbox, text)]
        last_y = y
    
    if len(current_row) >= 3:
        rows.append(current_row)
    
    # 检测连续的行（可能是表格）
    if len(rows) >= 3:
        tables.append({
            "type": "可能的表格区域",
            "rows": len(rows),
            "blocks": sum(len(r) for r in rows),
            "suggestion": "建议人工核对表格内容的完整性和准确性"
        })
    
    return tables


def detect_seal_regions(ocr_result, img_width, img_height):
    """
    检测可能的印章/签名区域
    印章特征：小块、圆形分布、通常在角落
    """
    seals = []
    
    for bbox, text, conf in ocr_result:
        if conf > 0.7:  # 高置信度
            # 计算块的大小
            width = bbox[1][0] - bbox[0][0]
            height = bbox[2][1] - bbox[1][1]
            
            # 印章通常是小块，文字短
            if width < img_width * 0.15 and height < img_height * 0.1:
                if len(text) < 10 and any(char in text for char in ['章', '印', '签名', '签字']):
                    seals.append({
                        "text": text,
                        "confidence": round(conf, 2),
                        "suggestion": "可能是印章或签名，建议核对"
                    })
    
    return seals


def extract_pdf_ocr(pdf_path, output_dir=None, lang="ch_sim", dpi=300):
    """
    从PDF扫描件中提取OCR文本（使用EasyOCR）
    
    新增：输出待办清单，标记可疑识别和遗漏区域

    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录（默认为PDF所在目录）
        lang: OCR语言，默认为简体中文。支持: ch_sim(简中), ch_tra(繁中), en(英), 组合如"ch_sim+en"
        dpi: 图像分辨率，默认300

    Returns:
        dict: 包含提取结果的字典，新增 review_items 字段
    """
    from pdf2image import convert_from_path
    import easyocr

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

    if output_dir is None:
        output_dir = pdf_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # 设置文件名
    base_name = pdf_path.stem
    output_txt = output_dir / f"{base_name}_ocr.txt"
    output_json = output_dir / f"{base_name}_ocr.json"

    print(f"正在处理: {pdf_path.name}")
    print(f"OCR引擎: EasyOCR")
    print(f"语言: {lang}")
    print(f"DPI: {dpi}")
    print("-" * 50)

    # 转换PDF为图片
    print("步骤1: 转换PDF为图片...")
    try:
        images = convert_from_path(str(pdf_path), dpi=dpi)
        print(f"  共 {len(images)} 页")
    except Exception as e:
        print(f"  错误: PDF转换失败 - {e}")
        print("  请确认Poppler已正确安装并添加到PATH")
        return None

    # 初始化EasyOCR阅读器（只初始化一次，复用）
    print("\n步骤2: 初始化EasyOCR引擎...")
    print("  （首次使用会自动下载模型，约100MB，请耐心等待）")
    try:
        # 解析语言列表
        lang_list = lang.split('+')
        reader = easyocr.Reader(lang_list, gpu=False, verbose=False)
        print("  * OCR引擎初始化完成")
    except Exception as e:
        print(f"  - 初始化失败: {e}")
        print(f"  Check network connection")
        return None

    # OCR识别
    print("\n步骤3: 进行OCR识别...")
    results = {
        "pdf_file": str(pdf_path),
        "pages": len(images),
        "dpi": dpi,
        "language": lang,
        "ocr_engine": "EasyOCR",
        "pages_content": [],
        "review_items": []  # 新增：待人工核对清单
    }

    full_text_parts = []

    for i, image in enumerate(images, 1):
        print(f" 处理第 {i}/{len(images)} 页...", end=" ")
        try:
            # 将PIL Image转换为numpy数组
            import numpy as np
            img_array = np.array(image)
            img_height, img_width = img_array.shape[:2]

            # 进行OCR
            # result格式: [[bbox, text, confidence], ...]
            ocr_result = reader.readtext(img_array, detail=1)
            
            # 页面级审查项
            page_review_items = {
                "page": i,
                "low_confidence_items": [],  # 低置信度文本
                "possible_tables": [],       # 可能的表格区域
                "possible_seals": [],        # 可能的印章/签名
                "special_chars": []          # 特殊字符/乱码
            }

            # 提取文本并按行组织
            lines = []
            current_line_y = None
            line_threshold = img_height * 0.02

            for bbox, text, conf in ocr_result:
                # 低置信度检测（< 0.5）
                if conf < 0.5:
                    page_review_items["low_confidence_items"].append({
                        "text": text,
                        "confidence": round(conf, 2),
                        "suggestion": "置信度低，建议人工核对"
                    })
                
                # 特殊字符/乱码检测
                if text and (len(text) < 2 or any(ord(c) > 0x9FFF or ord(c) < 0x4E00 for c in text if '\u4e00' <= c <= '\u9fff')):
                    # 包含非中文字符或太短
                    if any(c.isdigit() or c.isalpha() for c in text):
                        pass  # 数字或字母是正常的
                    else:
                        page_review_items["special_chars"].append({
                            "text": text,
                            "confidence": round(conf, 2),
                            "suggestion": "可能包含乱码或特殊符号，建议核对"
                        })
                
                if conf > 0.3: # 只保留置信度>30%的结果用于正文
                    lines.append(text)

            # 检测表格区域
            page_review_items["possible_tables"] = detect_table_regions(ocr_result, img_height, img_width)
            
            # 检测印章区域
            page_review_items["possible_seals"] = detect_seal_regions(ocr_result, img_width, img_height)
            
            # 汇总审查项
            if any(page_review_items[k] for k in ["low_confidence_items", "possible_tables", "possible_seals", "special_chars"]):
                results["review_items"].append(page_review_items)

            text = '\n'.join(lines)

            page_data = {
                "page": i,
                "text": text,
                "char_count": len(text.strip()),
                "ocr_blocks": len(ocr_result),
                "review_count": len([x for x in [page_review_items["low_confidence_items"], 
                                                 page_review_items["special_chars"]] if x])
            }
            results["pages_content"].append(page_data)
            full_text_parts.append(f"\n=== PAGE {i} ===\n{text}")
            
            review_marker = " ⚠️" if results["review_items"] and results["review_items"][-1]["page"] == i else ""
            print(f"* ({len(text.strip())} 字符, {len(ocr_result)} 文本块){review_marker}")

        except Exception as e:
            print(f"- 错误: {e}")
            results["pages_content"].append({
                "page": i,
                "text": "",
                "char_count": 0,
                "error": str(e),
                "review_count": 0
            })

    # 保存文本文件
    print(f"\n步骤4: 保存结果...")
    full_text = "\n".join(full_text_parts)

    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"  文本文件: {output_txt}")

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  JSON文件: {output_json}")

    # 生成待办核对清单文件
    print("\n步骤4: 生成待办核对清单...")
    review_md_path = output_dir / f"{base_name}_ocr_待办核对.md"
    
    review_md_content = f"""# OCR 识别待办核对清单

**源文件**: {pdf_path.name}
**处理时间**: {results['pages_content'][0].get('analyzed_at', 'N/A') if results['pages_content'] else 'N/A'}
**OCR引擎**: EasyOCR
**语言**: {lang}
**总页数**: {len(images)}

---

## ⚠️ 需要人工核对的项目

**重要提示**: OCR 识别存在局限性，以下区域需要人工核对确认：

1. **低置信度文本**（识别不确定）
2. **表格区域**（OCR难以完整还原表格结构）
3. **印章/签名**（可能影响法律效力判断）
4. **特殊字符**（可能为乱码或识别错误）

---

"""
    
    if results["review_items"]:
        for item in results["review_items"]:
            review_md_content += f"\n### 第 {item['page']} 页\n\n"
            
            # 低置信度项
            if item["low_confidence_items"]:
                review_md_content += "#### 🔍 低置信度文本（需核对）\n\n"
                for low_conf in item["low_confidence_items"]:
                    review_md_content += f"- 识别内容: `{low_conf['text']}`\n"
                    review_md_content += f"  - 置信度: {low_conf['confidence']}\n"
                    review_md_content += f"  - 建议: {low_conf['suggestion']}\n\n"
            
            # 表格区域
            if item["possible_tables"]:
                review_md_content += "#### 📊 可能的表格区域\n\n"
                for table in item["possible_tables"]:
                    review_md_content += f"- **{table['type']}**\n"
                    review_md_content += f"  - 检测到的行数: {table['rows']}\n"
                    review_md_content += f"  - 文本块数量: {table['blocks']}\n"
                    review_md_content += f"  - 建议: {table['suggestion']}\n\n"
            
            # 印章区域
            if item["possible_seals"]:
                review_md_content += "#### 🖋️ 可能的印章/签名区域\n\n"
                for seal in item["possible_seals"]:
                    review_md_content += f"- 识别内容: `{seal['text']}`\n"
                    review_md_content += f"  - 置信度: {seal['confidence']}\n"
                    review_md_content += f"  - 建议: {seal['suggestion']}\n\n"
            
            # 特殊字符
            if item["special_chars"]:
                review_md_content += "#### ⚡ 特殊字符/乱码警告\n\n"
                for spec in item["special_chars"]:
                    review_md_content += f"- 识别内容: `{spec['text']}`\n"
                    review_md_content += f"  - 置信度: {spec['confidence']}\n"
                    review_md_content += f"  - 建议: {spec['suggestion']}\n\n"
    else:
        review_md_content += "\n✅ **本页识别置信度较高，未发现明显需要核对的区域**\n\n"
        review_md_content += "但请注意：OCR 仍可能存在以下遗漏：\n"
        review_md_content += "- 手写批注未识别\n"
        review_md_content += "- 复杂版式（多栏/图文混排）排版错乱\n"
        review_md_content += "- 印章骑缝章遮挡文字\n\n"
    
    review_md_content += """---

## 📝 人工核对建议

### 核对优先级（高→低）

1. **涉及金额、数量的数字** → 最容易识别错误
2. **审批人姓名/签名** → 法律效力关键
3. **日期字段** → 影响时间线判断
4. **表格数据** → OCR 难以还原结构
5. **印章文字** → 可能模糊不清

### 核对方法

- 对比原始 PDF，逐页核对关键字段
- 重点关注被标记为"低置信度"的区域
- 检查表格是否完整，行列是否对应正确
- 确认印章、签名的识别是否准确

### 补充纠正

如发现识别错误：
1. 打开 `{base_name}_ocr.txt` 文件
2. 手动修改错误内容
3. 在修订处添加注释：`[人工修正]`
4. 保存后重新运行 document-organizer 分析

---

**注意**: 本清单仅标记可疑区域，不代表实际错误。请以原始 PDF 为准进行核对。
"""
    
    with open(review_md_path, "w", encoding="utf-8") as f:
        f.write(review_md_content)
    print(f" 待办核对清单: {review_md_path}")

    # 生成摘要
    total_chars = sum(p.get("char_count", 0) for p in results["pages_content"])
    success_pages = sum(1 for p in results["pages_content"] if not p.get("error"))
    total_blocks = sum(p.get("ocr_blocks", 0) for p in results["pages_content"] if not p.get("error"))
    total_review_items = len(results["review_items"])
    pages_need_review = len(set(item["page"] for item in results["review_items"]))

    print("\n" + "=" * 50)
    print("处理完成!")
    print(f" 总页数: {len(images)}")
    print(f" 成功页数: {success_pages}")
    print(f" 失败页数: {len(images) - success_pages}")
    print(f" 总字符数: {total_chars}")
    print(f" OCR文本块: {total_blocks}")
    print(f" 平均每页: {total_chars // len(images) if images else 0} 字符")
    print(f" 需核对页数: {pages_need_review}/{len(images)}")
    print("=" * 50)
    
    if total_review_items > 0:
        print(f"\n⚠️  发现 {total_review_items} 项需要人工核对的内容")
        print(f"   请查看: {review_md_path.name}")
    else:
        print(f"\n✅ 识别置信度较高")
        print(f"   但仍建议查看核对清单确认: {review_md_path.name}")
    print("=" * 50)

    return results


def batch_process(directory, lang="ch_sim"):
    """批量处理目录中的所有PDF"""
    pdf_files = sorted(Path(directory).glob("*.pdf"))

    if not pdf_files:
        print(f"目录中没有PDF文件: {directory}")
        return

    print(f"发现 {len(pdf_files)} 个PDF文件")
    print("=" * 50)

    for pdf_file in pdf_files:
        try:
            extract_pdf_ocr(pdf_file, lang=lang)
            print("\n")
        except Exception as e:
            print(f"处理失败 [{pdf_file.name}]: {e}\n")


def show_help():
    """显示帮助信息"""
    print(__doc__)
    print("\n" + "=" * 60)
    print("用法示例:")
    print("  " + "-" * 60)
    print("  单文件处理:")
    print('    python pdf_ocr_extractor.py "NPM001.pdf"')
    print("  " + "-" * 60)
    print("  指定输出目录:")
    print('    python pdf_ocr_extractor.py "NPM001.pdf" "./output"')
    print("  " + "-" * 60)
    print("  指定语言（纯中文）:")
    print('    python pdf_ocr_extractor.py "NPM001.pdf" "./output" "ch_sim"')
    print("  " + "-" * 60)
    print("  指定语言（中英文混合）:")
    print('    python pdf_ocr_extractor.py "NPM001.pdf" "./output" "ch_sim+en"')
    print("  " + "-" * 60)
    print("  批量处理（推荐用于制度分析）:")
    print('    python pdf_ocr_extractor.py --batch "./policies" "ch_sim"')
    print("=" * 60)
print("\n推荐用于内部审计制度分析:")
print(" python pdf_ocr_extractor.py --batch \"internal-audit-workspace/documents\" \"ch_sim\"")


def main():
    """主程序入口"""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        show_help()
        sys.exit(0)

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    if not check_system_dependencies():
        sys.exit(1)

    # 解析参数
    if sys.argv[1] == "--batch":
        # 批量模式
        if len(sys.argv) < 3:
            print("错误: 批量模式需要指定目录")
            print("示例: python pdf_ocr_extractor.py --batch \"./policies\" \"ch_sim\"")
            sys.exit(1)
        batch_process(sys.argv[2], lang=sys.argv[3] if len(sys.argv) > 3 else "ch_sim")
    else:
        # 单文件模式
        pdf_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        lang = sys.argv[3] if len(sys.argv) > 3 else "ch_sim"

        try:
            result = extract_pdf_ocr(pdf_path, output_dir, lang)
            if result is None:
                sys.exit(1)
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
