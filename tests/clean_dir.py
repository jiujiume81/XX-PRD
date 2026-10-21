#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删除一个目录，**删不掉必须留痕**（XX-029）。

为什么单独抽出来：清理是测试的前置条件，可它原来把失败降级成"无事发生"：

    clean_dir() { python3 -c 'import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)' "$1"; }

`ignore_errors=True` 让"删失败"和"本来就没有"长得一模一样。于是"这次跑用的是不是干净目录"
变成不可观测变量：该红的红不了，该报 ENV 的被伪装成"少几条断言"，而人的第一反应是重跑一次 ——
重跑恰好会因为残留状态变化而"好了"，把环境缺陷固化成偶发。

实测过的代价：旧路径 tests/.build/profiles 的 clean_dir 一次都没删成功（954 个文件 / 13MB），
第 2 次连跑掉到 754/4（Chrome 复用带旧 localStorage 的 profile）。

用法:
    python3 tests/clean_dir.py <目录>

退出码:
    0 = 目录不存在，或已删掉
    2 = 删完仍在（打印 CLEAN_FAILED=<绝对路径> 与 OSError 文本）
    64 = 用法错误
"""

import shutil
import sys
from pathlib import Path


def clean_dir(path):
    """返回 0 / 2；删失败时把 CLEAN_FAILED 一行打到 stdout。

    不用 ignore_errors：要拿得到异常文本，否则"删不掉"只剩一个布尔值，
    下一次排障还得自己复现一遍 chmod。
    """
    # 空路径必须挡在最前面：`Path("")` 等于当前目录 `.`，而 `.` 是存在的 ——
    # 一旦上游因为 mktemp 失败传进来一个空字符串，下一步就是删掉工作目录。
    # 这个护栏不是防御式编程的洁癖，是"上游确实会产生空串"（run.sh 的 PROF_ROOT）。
    if path is None or not str(path).strip():
        print("CLEAN_FAILED=<空路径> 拒绝删除：空串会被解析成当前目录", file=sys.stderr)
        return 2
    p = Path(path)
    try:
        abspath = str(p.absolute())
    except OSError:
        abspath = str(p)
    if not p.exists():
        return 0                      # 本来就没有 = 干净，不是失败
    try:
        shutil.rmtree(p)
    except OSError as e:
        print("CLEAN_FAILED=%s (%s: %s)" % (abspath, type(e).__name__, e))
        return 2
    if p.exists():
        # rmtree 不抛异常但仍存在（部分删除 / 被策略拦成 no-op）
        print("CLEAN_FAILED=%s (仍存在，rmtree 未报错)" % abspath)
        return 2
    return 0


def main(argv):
    if len(argv) != 2:
        print("用法: python3 tests/clean_dir.py <目录>", file=sys.stderr)
        return 64
    return clean_dir(argv[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
