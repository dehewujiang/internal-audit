#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON文件格式验证脚本 - 全局版本
用于验证任意项目目录下所有JSON文件的语法正确性

用法:
    python validate-json.py <directory> [options]

选项:
    --pattern <glob>  指定匹配模式 (默认: *.json)
    --recursive       递归子目录 (默认启用)
    --exit-on-error   发现错误时立即退出

[OUTPUT]: 人话报告 + 尾行 SHEET 答卷（action=pass/block），exit 0=pass / 2=block或目录错误
[POS]:    B3b 起纳入答卷体系；人话模式尾行追 SHEET，B0 契约测试覆盖
"""
import json
import sys
from pathlib import Path
import argparse


def validate_json_file(file_path):
    """验证单个JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True, None
    except json.JSONDecodeError as e:
        return False, f"line {e.lineno}, col {e.colno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def validate_directory(directory, pattern="*.json", recursive=True, exit_on_error=False):
    """验证目录下所有匹配模式的JSON文件。返回 (success, passed[], errors[])。"""
    dir_path = Path(directory).resolve()
    if not dir_path.exists():
        print(f"[ERROR] Directory not found: {directory}")
        return False, [], [(directory, "目录不存在")]

    if recursive:
        json_files = list(dir_path.rglob(pattern))
    else:
        json_files = list(dir_path.glob(pattern))

    if not json_files:
        print(f"[INFO] No JSON files found in: {directory}")
        return True, [], []

    errors = []
    passed = []

    print(f"\n{'='*60}")
    print(f"JSON Validation Report")
    print(f"Directory: {dir_path}")
    print(f"Pattern: {pattern}, Recursive: {recursive}")
    print(f"{'='*60}\n")

    for f in sorted(json_files):
        relative_path = f.relative_to(dir_path)
        success, error = validate_json_file(f)
        if success:
            passed.append(str(relative_path))
            print(f"  [PASS] {relative_path}")
        else:
            errors.append((str(relative_path), error))
            print(f"  [FAIL] {relative_path}")
            print(f"         Error: {error}")
            if exit_on_error:
                print(f"\n{'='*60}")
                print(f"Exiting early due to --exit-on-error flag")
                return False, passed, errors

    print(f"\n{'='*60}")
    print(f"Summary: {len(passed)} passed, {len(errors)} failed")
    print(f"{'='*60}\n")

    if errors:
        print("[FAIL] Validation failed. Please fix the errors above before proceeding.")
        return False, passed, errors

    print("[PASS] All JSON files are valid.")
    return True, passed, errors


def main():
    parser = argparse.ArgumentParser(description='Validate JSON files in a directory')
    parser.add_argument('directory', help='Directory to validate')
    parser.add_argument('--pattern', default='*.json', help='File pattern to match')
    parser.add_argument('--recursive', action='store_true', default=True, help='Recursively search subdirectories')
    parser.add_argument('--exit-on-error', action='store_true', help='Exit immediately on first error')
    parser.add_argument('--no-recursive', dest='recursive', action='store_false', help='Do not search subdirectories')

    args = parser.parse_args()

    success, passed, errors = validate_directory(
        args.directory,
        pattern=args.pattern,
        recursive=args.recursive,
        exit_on_error=args.exit_on_error
    )

    # 结构化答卷（B3b）：人话模式尾行追 SHEET。通用 JSON 只有 pass/block 两档，
    # block → exit 2（闸机回退通道把 ≥2 当阻断，不会误判成警告放行）。
    action = "pass" if success else "block"
    details = [{"check": "json_syntax", "result": "fail" if e else "pass",
                "message": f"{p}: {e}" if e else p}
               for p, e in ([(p, None) for p in passed] +
                            [(p, m) for p, m in errors])]
    print("SHEET:" + json.dumps({
        "tool": "validate-json",
        "action": action,
        "message": f"{len(passed)} 通过, {len(errors)} 失败" if not success else "全部 JSON 合法",
        "summary": {"total": len(passed) + len(errors), "passed": len(passed),
                    "warned": 0, "blocked": len(errors)},
        "details": details,
        "crashed": False,
    }, ensure_ascii=False))

    sys.exit(0 if success else 2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # 未预期崩溃 → 先吐 block 答卷再 exit 2
        import traceback
        print("SHEET:" + json.dumps({
            "tool": "validate-json",
            "action": "block",
            "message": "脚本崩溃，已转拦下",
            "summary": {"total": 0, "passed": 0, "warned": 0, "blocked": 1},
            "details": [],
            "crashed": True,
        }, ensure_ascii=False))
        traceback.print_exc()
        sys.exit(2)