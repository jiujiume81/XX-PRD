#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R1-R9：CSS 取值纪律（静态文本判据）。规格见 项目治理/迭代/I-05-UI审美方案.md §6.2。

为什么是"取值集合"而不是"看截图"：
  19 档字号 × 35 种彩色 × 77 根同档 1px 描边叠在 1080×675 里，所有元素重量趋同、
  没有主次，用户读作"乱/丑"。这些量可以数，数出来就能做成门。

用法:
    python3 tests/check_ui_scale.py                # 默认读 assets/container/index.html
    python3 tests/check_ui_scale.py --list         # 附带把每个脱档取值的行号打出来
    python3 tests/check_ui_scale.py --selfcheck    # G-2 自证：反例必须红在正确的规则上
    python3 tests/check_ui_scale.py FILE           # 指定容器文件（自证时用临时副本）

退出码:
    0 = 全 PASS
    1 = 有超限
    2 = 环境/输入问题（切片读不到、读多了、文件被截断）

口径变更纪律（§6.1）：
  任何一项改动口径（含/不含 JS、按声明还是按出现、四值简写折不折）都必须重定阈值，
  并在下面 CHANGELOG 里写一行「口径变更」。否则下一轮的 45 与这一轮的 77 量的不是同一样东西。

CHANGELOG
  2026-10-21 首版。口径逐条对齐 §6.1/§6.2，并与方案文档的诊断基线逐数核对：
             css=52016 字符/706 行、R1=35、R2a=19、R4=15、R5a=28、R5b=9、R6=77、R7=11。
             若这里和方案文档对不上，先对齐口径，不许各改各的阈值。
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTAINER = ROOT / "assets" / "container" / "index.html"

# ---------------------------------------------------------------- 阈值（决定，不是测量）
# 这些是"决定"：改它要改 backlog 条目 XX-028，不能改脚本。理由见 §6.2 的注。
R1_MAX_COLORS = 12
R2A_MAX_SIZES = 5
R2B_ALLOWED = {"12px", "14px", "16px", "20px", "32px"}
R3_ALLOWED = {"400", "500", "600"}
R4_ALLOWED = {"0", "2px", "4px", "6px", "8px", "50%",
              "var(--ant-radius)", "var(--ant-radius-lg)"}
R5A_MAX = 8               # 软指标：只报不打红（见 R5a 行）
R6_MAX_BORDERS = 45       # 决定：现状 77，目标砍 42%
R7_MAX_SHADOWS = 3

# 切片守卫（§6.5 G-3）。四种成因必须打不同首词：前两种是脚本读错了东西，后两种是文件结构真变了。
SLICE_MIN_CSS_CHARS = 20000
SLICE_MIN_CSS_LINES = 300
SLICE_RATIO = (0.05, 0.40)
SLICE_MIN_TOTAL_CHARS = 10000


# ---------------------------------------------------------------- 切片（§6.1）
class EnvError(Exception):
    """环境/输入问题：退 2，不计入超限数。首词决定处置方向，不许合并成 SLICE。"""


def load_slice(path):
    src = Path(path).read_text(encoding="utf-8")
    lines = src.split("\n")

    n_open = src.count("<style")
    n_close = src.count("</style>")
    if n_open != 1 or n_close != 1:
        raise EnvError("ENV-ANCHOR style=%d /style=%d 期望各 1" % (n_open, n_close))

    idx_open = [i for i, l in enumerate(lines) if "<style>" in l]
    idx_close = [i for i, l in enumerate(lines) if "</style>" in l]
    if not idx_open or not idx_close:
        # 含 "<style" 但不是裸 "<style>"（例如带属性）：锚点找不到，属脚本读错的东西
        raise EnvError("ENV-ANCHOR 找不到裸 <style> / </style> 行，锚点不可用")

    s, e = idx_open[0] + 1, idx_close[0]
    if e <= s:
        raise EnvError("ENV-ANCHOR </style> 在 <style> 之前（行 %d / %d）" % (s + 1, e + 1))
    css = "\n".join(lines[s:e])

    total = len(src)
    if total < SLICE_MIN_TOTAL_CHARS:
        raise EnvError("ENV-TOTAL 全文=%d 下界 %d" % (total, SLICE_MIN_TOTAL_CHARS))
    if len(css) < SLICE_MIN_CSS_CHARS or len(css.split("\n")) < SLICE_MIN_CSS_LINES:
        raise EnvError("ENV-SHORT css=%d 行=%d 下界 %d/%d"
                       % (len(css), len(css.split("\n")), SLICE_MIN_CSS_CHARS, SLICE_MIN_CSS_LINES))
    ratio = len(css) / total
    if not (SLICE_RATIO[0] <= ratio <= SLICE_RATIO[1]):
        raise EnvError("ENV-RATIO %d/%d = %.1f%% 带 %d%%–%d%%"
                       % (len(css), total, ratio * 100,
                          SLICE_RATIO[0] * 100, SLICE_RATIO[1] * 100))
    return src, css, s


# ---------------------------------------------------------------- 解析
def strip_comments(css):
    """注释换成等长空格：位移不变（行号可直接用），但注释里的词不再算证据。

    这是 §6.5 G-4 的实现核心：`re.findall("tabular-nums")` 会命中
    `/* 这里用 tabular-nums */`——有词 ≠ 有声明。
    """
    return re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group()), css, flags=re.S)


DECL_RE = re.compile(r"([-a-zA-Z]+)\s*:\s*([^;{}]+)")


def iter_rules(css, prefix=""):
    """叶规则 (selector, body, body_offset_in_css)。@media/@supports/@keyframes 递归进去。"""
    i = 0
    buf = ""
    n = len(css)
    while i < n:
        ch = css[i]
        if ch == "{":
            depth = 1
            j = i + 1
            while j < n and depth:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                j += 1
            body = css[i + 1:j - 1]
            sel = " ".join(buf.split())
            if sel.startswith("@"):
                # 分组 at-rule 递归；@keyframes 里的 "0%,100%" 也是块，一并递归（其声明照样计数）
                yield from iter_rules(body, (prefix + " " + sel).strip())
            elif sel:
                yield (prefix + " " + sel).strip(), body, i + 1
            buf = ""
            i = j
        else:
            buf += ch
            i += 1


def parse_decls(css_nc):
    """[(selector, prop, value, file_off_in_css)]"""
    out = []
    for sel, body, off in iter_rules(css_nc):
        for m in DECL_RE.finditer(body):
            out.append((sel, m.group(1).lower(), " ".join(m.group(2).split()), off + m.start()))
    return out


def in_keyframes(sel):
    return "@keyframes" in sel or "@-webkit-keyframes" in sel


# ---------------------------------------------------------------- 取值归一
def _rgb_from_hex(h):
    h = h.lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 4:                       # #RGBA
        h = "".join(c * 2 for c in h[:3])
    if len(h) in (6, 8):
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return None


def is_colored(rgb):
    return rgb is not None and (max(rgb) - min(rgb)) > 12


def collect_colors(text):
    """R1 归一：hex 小写展开 6 位；rgba 去空白（保留 alpha，因为 alpha 不同的发光是不同取值）。"""
    hexes, rgbas = set(), set()
    for m in re.finditer(r"#([0-9a-fA-F]{3,8})", text):
        h = m.group(1)
        rgb = _rgb_from_hex(h)
        if is_colored(rgb):
            hh = h.lower()
            if len(hh) == 3:
                hh = "".join(c * 2 for c in hh)
            hexes.add("#" + hh[:6])
    for m in re.finditer(r"rgba?\(([^)]*)\)", text):
        body = re.sub(r"\s+", "", m.group(1))
        try:
            rgb = tuple(float(x) for x in body.split(",")[:3])
        except ValueError:
            continue
        if is_colored(rgb):
            rgbas.add("rgb(%s)" % body)
    return hexes, rgbas


# ---------------------------------------------------------------- 判据
class Report:
    def __init__(self, path, show_list=False):
        self.path = path
        self.show_list = show_list
        self.rows = []          # (id, 描述, 现值, 阈值, ok)
        self.fails = []
        self.numeric = {}       # rid -> int（现值不是整数时为 None）

    def add(self, rid, desc, actual, limit, ok, offenders=None):
        self.rows.append((rid, desc, actual, limit, ok))
        self.numeric[rid] = actual if isinstance(actual, int) else None
        if not ok:
            self.fails.append(rid)
            if self.show_list and offenders:
                for o in offenders[:40]:
                    print("      - %s" % o)
                if len(offenders) > 40:
                    print("      - ... 另 %d 处" % (len(offenders) - 40))

    def render(self):
        for rid, desc, actual, limit, ok in self.rows:
            print("%-4s %-14s %-24s 阈值 %-14s %s"
                  % (rid, desc, actual, limit, "PASS" if ok else "FAIL"))
        print("RESULT %s (%d 项超限)" % ("PASS" if not self.fails else "FAIL", len(self.fails)))
        return 0 if not self.fails else 1


def check(src, css, css_start_line, show_list=False):
    rep = Report(None, show_list)
    nc = strip_comments(css)                      # 所有文本判据都跑在去注释文本上
    decls = parse_decls(nc)

    def line_of(off):
        return css_start_line + nc[:off].count("\n") + 1

    # ---- R1 彩色取值个数
    hexes, rgbas = collect_colors(nc)
    colors = hexes | rgbas
    rep.add("R1", "彩色取值个数", len(colors), "<= %d" % R1_MAX_COLORS,
            len(colors) <= R1_MAX_COLORS, sorted(colors))

    # ---- R2a 字号档数 / R2b 字号脱档
    fs_literals = {}                              # value -> [line, ...]
    for sel, prop, val, off in decls:
        if prop == "font-size" and re.fullmatch(r"\d+(?:\.\d+)?px", val):
            if float(val[:-2]) == 0:
                continue                          # font-size:0 不计
            fs_literals.setdefault(val, []).append(line_of(off))
    rep.add("R2a", "字号档数", len(fs_literals), "<= %d" % R2A_MAX_SIZES,
            len(fs_literals) <= R2A_MAX_SIZES, sorted(fs_literals))
    off_sizes = [(v, ls) for v, ls in fs_literals.items() if v not in R2B_ALLOWED]
    rep.add("R2b", "字号脱档", len(off_sizes), "0",
            not off_sizes,
            ["%s  (行 %s)" % (v, ",".join(map(str, ls[:4]))) for v, ls in sorted(off_sizes)])

    # ---- R3 字重
    weights = {}
    for sel, prop, val, off in decls:
        if prop == "font-weight":
            v = {"normal": "400", "bold": "700"}.get(val.lower(), val.lower())
            weights.setdefault(v, []).append(line_of(off))
    bad_w = [v for v in weights if v not in R3_ALLOWED]
    rep.add("R3", "字重脱档", len(bad_w), "0 且档数<=3",
            not bad_w and len(weights) <= 3,
            ["%s (行 %s)" % (v, ",".join(map(str, weights[v][:4]))) for v in sorted(bad_w)])

    # ---- R4 圆角
    radii = {}
    for sel, prop, val, off in decls:
        if prop != "border-radius":
            continue
        t = val
        if t in ("0", "0px"):
            t = "0"
        parts = t.split(" ")
        if len(parts) == 4 and len(set(parts)) == 1:
            t = parts[0]                          # 四值相同折叠为一值
        radii.setdefault(t, []).append(line_of(off))
    bad_r = [v for v in radii if v not in R4_ALLOWED]
    rep.add("R4", "圆角脱档", len(bad_r), "0",
            not bad_r,
            ["%s (行 %s)" % (v, ",".join(map(str, radii[v][:4]))) for v in sorted(bad_r)])

    # ---- R5a 间距取值数（软指标：只报不打红）/ R5b 间距脱栅
    spacing = {}
    for sel, prop, val, off in decls:
        if not re.fullmatch(r"(padding|margin|gap)(-(top|right|bottom|left))?", prop):
            continue
        for tok in val.split():                   # 简写拆 token：padding:8px 16px 贡献两个取值
            if re.fullmatch(r"-?\d+(?:\.\d+)?px", tok):
                spacing.setdefault(float(tok[:-2]), []).append(line_of(off))
    rep.add("R5a", "间距取值数", len(spacing), "<= %d(软)" % R5A_MAX, True,
            sorted(spacing))
    off_grid = sorted(v for v in spacing if v != 0 and abs(int(v)) % 2 != 0)
    rep.add("R5b", "间距脱栅", len(off_grid), "0",
            not off_grid,
            ["%spx (行 %s)" % (int(v), ",".join(map(str, spacing[v][:4]))) for v in off_grid])

    # ---- R6 1px 描边次数（按字面出现，只数简写 1px solid）
    border_hits = [m.start() for m in
                   re.finditer(r"(?<![-\w])border(?:-(?:top|right|bottom|left))?\s*:\s*1px\s+solid", nc)]
    rep.add("R6", "1px 描边次数", len(border_hits), "<= %d" % R6_MAX_BORDERS,
            len(border_hits) <= R6_MAX_BORDERS,
            ["行 %d" % line_of(o) for o in border_hits])

    # ---- R7 阴影取值数
    shadows = {}
    for sel, prop, val, off in decls:
        if prop == "box-shadow" and val.lower() != "none":
            shadows.setdefault(re.sub(r"\s*,\s*", ",", val), []).append(line_of(off))
    rep.add("R7", "阴影取值数", len(shadows), "<= %d" % R7_MAX_SHADOWS,
            len(shadows) <= R7_MAX_SHADOWS,
            ["%s (行 %s)" % (v, ",".join(map(str, shadows[v][:3]))) for v in sorted(shadows)])

    # ---- R8 令牌区外硬编码彩色
    # 口径（§6.2 原文）：tokens = css[:css.index("}")+1]（= 第一个块），body = 其余。
    first = nc.index("}")
    tokens_block, rest = nc[:first + 1], nc[first + 1:]
    rest_off = first + 1
    hard = {}                                     # 按 R1 的集合语义去重；出现次数另计
    for m in re.finditer(r"#([0-9a-fA-F]{3,8})", rest):
        if not is_colored(_rgb_from_hex(m.group(1))):
            continue
        h = m.group(1).lower()
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        hard.setdefault("#" + h[:6], []).append(line_of(rest_off + m.start()))
    rep.add("R8", "令牌区外硬编码彩色",
            "%d 种/%d 处" % (len(hard), sum(len(v) for v in hard.values())),
            "0 种", not hard,
            ["%s (行 %s)" % (v, ",".join(map(str, ls[:4]))) for v, ls in sorted(hard.items())])

    # ---- R9 数字等宽覆盖（必须锚定到「选择器 + 属性声明」）
    # 判据：存在一条规则，选择器含 body 或 .ant-table，且声明里有 font-variant-numeric: tabular-nums。
    # 不接受"散点 4 处"：散点必然漏列；也不接受搜词：注释里的词不是声明（G-4）。
    hits = []
    for sel, prop, val, off in decls:
        if prop != "font-variant-numeric":
            continue
        if "tabular-nums" not in val:
            continue
        if ("body" in sel or ".ant-table" in sel) and not in_keyframes(sel):
            hits.append((sel, line_of(off)))
    rep.add("R9", "全局等宽数字", "命中 %d 条" % len(hits), ">= 1",
            bool(hits),
            ["需要一条 body / .ant-table 选择器内的 font-variant-numeric: tabular-nums；"
             "当前只有 %s" % (sorted({s for s, _ in hits}) or "无")])

    return rep


# ---------------------------------------------------------------- 自证（§6.5 G-2 / G-3）
def _fail_set(rep):
    return {rid for rid, _, _, _, ok in rep.rows if not ok}


GREEN_TOKEN_ANCHOR = "  --ant-warn:#faad14;\n"


def green_container():
    """一个**能通过全部十条判据**的最小容器，且刻意贴在各阈值上。

    为什么需要它：§6.5 G-2 的判据是 `actual_FAIL_set == expected ∪ declared_extra`，
    它只在基线全绿时成立。第一版自证我拿真实容器当基线，结果反例的"增量"全是空集 ——
    因为 R1/R2b/R6 本来就红，再注入同类缺陷根本不改变失败集。**一个测不出缺陷的自证，
    看起来和"判据都对"一模一样。**

    第二个作用更重要：它证明"十条判据可以同时全绿"。做不到，"退出码 0"这个门槛就是
    不可达的，门本身在说谎。

    为什么各项要**贴着阈值**（R1=10/12、R2a=5/5、R3=3/3、R7=3/3）：
    G-2 的那几条反例是"再加一个就超"，基线离阈值远的话，加一个也超不了 ——
    自证会静默通过，而它什么都没证明。第一次跑就是这么错的：基线只有 3 档字号，
    注入 13px 后档数 4 ≤ 5，R2a 不红，连带项断不出来。
    """
    colors = ["#1677ff", "#52c41a", "#faad14", "#ff4d4f", "#722ed1",
              "#13c2c2", "#eb2f96", "#fa8c16", "#a0d911", "#2f54eb"]   # 10 种，阈值 12
    tokens = ["  --ant-c%d:%s;\n" % (i, c) for i, c in enumerate(colors)]
    tokens += ["  --ant-shadow-1:0 1px 2px rgba(0,0,0,.06);\n",
               "  --ant-shadow-2:0 2px 8px rgba(0,0,0,.1);\n",
               "  --ant-shadow-3:0 6px 18px rgba(0,0,0,.13);\n",   # 3 种，阈值 3
               GREEN_TOKEN_ANCHOR]

    rules = []
    sizes = ["12px", "14px", "16px", "20px", "32px"]                # 5 档，阈值 5
    weights = ["400", "500", "600"]                                 # 3 档，阈值 3
    for i in range(320):
        rules.append(".g%d{padding:%dpx;margin:%dpx;font-size:%s;font-weight:%s;"
                     "border-radius:4px;color:#111}"
                     % (i, 8 if i % 2 else 0, 4 if i % 3 else 6,
                        sizes[i % 5], weights[i % 3]))
        if i % 8 == 0:                                              # 40 根，阈值 45
            rules.append(".g%d{border:1px solid #999}" % i)
        if i % 100 == 0:
            rules.append(".s%d{box-shadow:var(--ant-shadow-%d)}" % (i, i % 3 + 1))
    # 间距取值集合刻意凑满 8 种（0/2/4/6/8/10/12/16），再加一个奇数就能红 R5b
    for v in (2, 10, 12, 16):
        rules.append(".p%d{padding:%dpx}" % (v, v))

    css = (
        ":root{\n" + "".join(tokens) + "}\n"
        "body{font-size:14px;font-weight:400;font-variant-numeric:tabular-nums;"
        "padding:0;margin:0;color:#111}\n"
        "h1{font-size:20px;font-weight:600}\n"
        "h2{font-size:32px;font-weight:500;border-radius:6px;box-shadow:var(--ant-shadow-2)}\n"
        "table td{font-size:12px;font-weight:400;border-radius:0}\n"
        + "\n".join(rules) + "\n"
    )
    filler = "".join("合规基线填充文本，只为把切片比例压进 5%%-40%% 的带内（这一段不是 CSS，"
                     "是 body 里的正文，用来当比例带的分母）。%04d\n" % i
                     for i in range(1400))
    return ("<html><head><style>\n%s</style></head>\n<body><div>%s</div></body></html>"
            % (css, filler))


def _add_to_tokens(extra):
    return lambda s: s.replace(GREEN_TOKEN_ANCHOR, GREEN_TOKEN_ANCHOR + extra, 1)


def _drop_body_tabular(s):
    """删掉 body 的真声明，只留注释里的词 —— R9 必须红，证明它认声明不认词。"""
    return (s.replace("font-variant-numeric:tabular-nums;", "", 1)
             .replace("body{", "/* body{font-variant-numeric:tabular-nums} */\nbody{", 1))


def _tabular_only_on_other_selector(s):
    """真声明存在，但选择器不是 body / .ant-table —— 「有声明」不等于「全局生效」。"""
    return (s.replace("font-variant-numeric:tabular-nums;", "", 1)
             .replace(GREEN_TOKEN_ANCHOR,
                      GREEN_TOKEN_ANCHOR + ".zbtn{font-variant-numeric:tabular-nums}\n", 1))


def selfcheck(container):
    """G-2：反例必须红在正确的规则上；G-3：四种切片失效必须退 2 且首词不同。"""
    print("== 先证明「十条判据可以同时全绿」（否则退出码 0 是不可达的门）")
    green_src = green_container()
    tmp_green = Path("/tmp/xx-prd-ui-scale-green.html")
    tmp_green.write_text(green_src, encoding="utf-8")
    try:
        src, css, ln = load_slice(tmp_green)
    except EnvError as ex:
        print("  合规基线自己过不了切片守卫：%s  SELFCHECK-FAIL" % ex)
        tmp_green.unlink(missing_ok=True)
        return 1
    base_rep = check(src, css, ln)
    base_fails = _fail_set(base_rep)
    print("  基线 SLICE %d 字符 / %d 行 / 比例 %.1f%%  失败集 %s"
          % (len(css), len(css.split("\n")), len(css) / len(src) * 100,
             sorted(base_fails) or "（空，全绿）"))
    if base_fails:
        for rid, desc, actual, limit, ok in base_rep.rows:
            if not ok:
                print("      %-4s %s = %s（阈值 %s）" % (rid, desc, actual, limit))
        print("  基线不是全绿的，下面的精确集合断言没有意义  SELFCHECK-FAIL")
        tmp_green.unlink(missing_ok=True)
        return 1
    print("  各判据现值: " + "  ".join(
        "%s=%s" % (rid, actual) for rid, _, actual, _, _ in base_rep.rows))

    print("== G-2：注入缺陷后，失败集必须精确等于 expected ∪ declared_extra")
    cases = [
        ("font-size:13px", lambda s: s.replace(
            "</style>", ".zz{font-size:13px}\n</style>", 1), {"R2b"}, {"R2a"}),
        ("font-weight:700", lambda s: s.replace(
            "</style>", ".zz{font-weight:700}\n</style>", 1), {"R3"}, set()),
        ("border-radius:11px", lambda s: s.replace(
            "</style>", ".zz{border-radius:11px}\n</style>", 1), {"R4"}, set()),
        ("box-shadow 第 4 种", lambda s: s.replace(
            "</style>", ".zz{box-shadow:0 1px 2px rgba(0,0,0,.2)}\n</style>", 1), {"R7"}, set()),
        ("margin:7px", lambda s: s.replace(
            "</style>", ".zz{margin:7px}\n</style>", 1), {"R5b"}, set()),
        ("多 30 根 1px 描边", lambda s: s.replace(
            "</style>", "".join(".b%d{border:1px solid #999}\n" % i for i in range(30)) + "</style>", 1),
         {"R6"}, set()),
        ("彩色值凑到 13 种（加在令牌区里）",
         _add_to_tokens("  --ant-x1:#aa1000;\n  --ant-x2:#00aa20;\n  --ant-x3:#0010aa;\n"),
         {"R1"}, set()),
        ("令牌区外硬编码彩色（用已有色值，不动 R1）",
         lambda s: s.replace("</style>", ".zz{color:#1677ff}\n</style>", 1), {"R8"}, set()),
        ("R9 的真声明写在 .zbtn 上（有声明但不是全局）",
         _tabular_only_on_other_selector, {"R9"}, set()),
        ("注释里提到 tabular-nums（伪证据，不能算通过）",
         lambda s: s.replace("</style>", "/* 这里用 tabular-nums：注释不是声明 */\n</style>", 1),
         set(), set()),
        ("删掉真声明、只留注释里的词", _drop_body_tabular, {"R9"}, set()),
    ]

    ok_all = True
    for name, mutate, expected, declared in cases:
        rep = _run_on(green_src, mutate)
        if rep is None:
            print("  %-42s 切片守卫挡住了（expected 应只红判据）  SELFCHECK-FAIL" % name)
            ok_all = False
            continue
        got = _fail_set(rep)
        want = expected | declared
        ok = got == want
        ok_all = ok_all and ok
        print("  %-42s got=%-16s want=%-16s %s"
              % (name, sorted(got) or "[]", sorted(want) or "[]", "OK" if ok else "SELFCHECK-FAIL"))
        if not ok:
            print("      expected 未红：%s｜多报（过宽规则替别人背锅）：%s"
                  % (sorted(expected - got), sorted(got - want)))

    print("  注：§6.5 的 `margin:7px` 行把 R5a 列为连带项，但 §6.2 写的是「软指标，先不打红」。"
          "两处冲突，本脚本按 §6.2 执行（R5a 不参与判定），故 declared_extra 为空。")

    # ---- G-3 切片守卫：四种成因必须打不同首词（用真实容器，因为要触发真实的结构失效）
    print("== G-3：四种切片失效必须退 2，且四个首词互不相同")
    real = Path(container).read_text(encoding="utf-8")
    guards = []
    guards.append(("ENV-ANCHOR",
                   real.replace("</style>", "</style><style></style>", 1), "两个 <style>"))
    guards.append(("ENV-SHORT",
                   re.sub(r"<style>.*?</style>", "<style>\n.a{color:red}\n</style>", real, flags=re.S),
                   "空切片"))
    head, _, tail = real.partition("</style>")
    guards.append(("ENV-RATIO", head + "\n" + ("\n.zz{color:#111}\n" * 6000) + "</style>" + tail,
                   "切片框到半个文件"))
    guards.append(("ENV-TOTAL", "<html><style>\n.a{color:red}\n</style></html>", "全文被截断"))

    got_words = []
    for want_word, content, why in guards:
        p = Path("/tmp/xx-prd-guard-%s.html" % want_word.lower())
        p.write_text(content, encoding="utf-8")
        try:
            load_slice(p)
            print("  %-12s %-16s 未触发（期望退 2）  SELFCHECK-FAIL" % (want_word, why))
            ok_all = False
        except EnvError as ex:
            word = str(ex).split()[0]
            got_words.append(word)
            mark = "OK" if word == want_word else "SELFCHECK-FAIL(实际 %s)" % word
            ok_all = ok_all and word == want_word
            print("  %-12s %-16s %-52s %s" % (want_word, why, str(ex)[:52], mark))
        finally:
            p.unlink(missing_ok=True)
    tmp_green.unlink(missing_ok=True)

    if len(set(got_words)) != len(got_words):
        print("  首词重复：四个守卫必须打不同首词，否则排障时要从头猜是哪一类  SELFCHECK-FAIL")
        ok_all = False
    else:
        print("  四个首词互不相同: %s  OK" % " ".join(got_words))

    print("RESULT %s (selfcheck)" % ("PASS" if ok_all else "FAIL"))
    return 0 if ok_all else 1


def _run_on(src, mutate):
    """在给定容器源上做一次文本变异并跑判据；切片守卫挡住时返回 None（自证里那本身是失败）。"""
    p = Path("/tmp/xx-prd-ui-scale-fx.html")
    p.write_text(mutate(src), encoding="utf-8")
    try:
        s, css, ln = load_slice(p)
    except EnvError:
        return None
    finally:
        p.unlink(missing_ok=True)
    return check(s, css, ln)


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True, description="R1-R9 静态取值纪律")
    ap.add_argument("container", nargs="?", default=str(DEFAULT_CONTAINER))
    ap.add_argument("--list", action="store_true", help="列出脱档取值的行号")
    ap.add_argument("--selfcheck", action="store_true", help="跑 G-2/G-3 反例自证")
    args = ap.parse_args(argv)

    if not Path(args.container).is_file():
        print("ENV 找不到容器文件: %s" % args.container)
        return 2

    if args.selfcheck:
        return selfcheck(args.container)

    try:
        src, css, ln = load_slice(args.container)
    except EnvError as ex:
        print(str(ex))
        return 2

    print("SLICE %d/%d = %.1f%% (带 %d%%-%d%%) css=%d 行 全文=%d 字符"
          % (len(css), len(src), len(css) / len(src) * 100,
             SLICE_RATIO[0] * 100, SLICE_RATIO[1] * 100,
             len(css.split("\n")), len(src)))
    print("      单位是字符不是字节（§6.1）：禁止用 os.path.getsize 比对阈值")

    rep = check(src, css, ln, show_list=args.list)
    rc = rep.render()
    if rc:
        print("      修法：取值收敛到令牌/栅格，不要调阈值（阈值是决定，改它要改条目 XX-028）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
