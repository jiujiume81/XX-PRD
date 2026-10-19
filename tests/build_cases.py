#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把示例 JSON + harness 注入容器，产出可 headless 运行的测试 HTML。

用法:
    python3 tests/build_cases.py <example.json|__embedded__> <harness.js> <out.html>

- `__embedded__`：直接用容器自带的 #iprd-data（00-embedded 用例），只追加 harness。
- 其他：用示例 JSON 替换 #iprd-data 的内容，再追加 harness。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTAINER = ROOT / "assets" / "container" / "index.html"
EXDIR = ROOT / "assets" / "examples"

DATA_RE = re.compile(
    r'(<script type="application/json" id="iprd-data">)(.*?)(</script>)', re.S
)


def build(example, harness_js, out_html):
    html = CONTAINER.read_text(encoding="utf-8")
    if example != "__embedded__":
        data = (EXDIR / example).read_text(encoding="utf-8").strip()
        m = DATA_RE.search(html)
        if not m:
            raise SystemExit("容器中找不到 #iprd-data 数据块")
        html = html[: m.start(2)] + "\n" + data + "\n" + html[m.end(2) :]

    js = Path(harness_js).read_text(encoding="utf-8")
    if "</body>" not in html:
        raise SystemExit("容器中找不到 </body>，无法注入 harness")
    html = html.replace("</body>", "<script>\n" + js + "\n</script>\n</body>", 1)

    out = Path(out_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("built %s (%d bytes)" % (out, len(html)))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    build(sys.argv[1], sys.argv[2], sys.argv[3])
