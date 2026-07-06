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
    """验证目录下所有匹配模式的JSON文件"""
    dir_path = Path(directory).resolve()
    if not dir_path.exists():
        print(f"[ERROR] Directory not found: {directory}")
        return False

    if recursive:
        json_files = list(dir_path.rglob(pattern))
    else:
        json_files = list(dir_path.glob(pattern))

    if not json_files:
        print(f"[INFO] No JSON files found in: {directory}")
        return True

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
                return False

    print(f"\n{'='*60}")
    print(f"Summary: {len(passed)} passed, {len(errors)} failed")
    print(f"{'='*60}\n")

    if errors:
        print("[FAIL] Validation failed. Please fix the errors above before proceeding.")
        return False

    print("[PASS] All JSON files are valid.")
    return True


def main():
    parser = argparse.ArgumentParser(description='Validate JSON files in a directory')
    parser.add_argument('directory', help='Directory to validate')
    parser.add_argument('--pattern', default='*.json', help='File pattern to match')
    parser.add_argument('--recursive', action='store_true', default=True, help='Recursively search subdirectories')
    parser.add_argument('--exit-on-error', action='store_true', help='Exit immediately on first error')
    parser.add_argument('--no-recursive', dest='recursive', action='store_false', help='Do not search subdirectories')

    args = parser.parse_args()

    success = validate_directory(
        args.directory,
        pattern=args.pattern,
        recursive=args.recursive,
        exit_on_error=args.exit_on_error
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()