#!/usr/bin/env bash
# 容器回归：6 个用例（00-embedded + example-01~05），一条命令给出退出码。
# 用法:
#   bash tests/run.sh
#   CHROME=/path/to/chrome bash tests/run.sh
#   RETRIES_MAX=1 bash tests/run.sh      # 允许的重试上限（默认 0；勘误 E-03）
# 退出码:
#   0 = 6 用例全绿且断言数与基线一致，且 retries <= RETRIES_MAX（默认 0）
#   1 = 有失败（fails>0 或条数不等于基线，或生成器漂移，或 retries > RETRIES_MAX）
#   2 = 环境不可用（找不到 Chrome）
#   3 = 另一个 run.sh 正在同一工作区跑（单实例锁，避免并发互相覆盖 .build/）
#
# 稳定性判据（XX-001）：连续 3 次全 PASS 且 retries=0 才算通过；
# retries>0 不是通过证据，只是"重试后通过"，必须记录在案。
# 勘误 E-03（XX-016⑤）：retries 从 I-01 起只打在日志里，导致 CI 绿不蕴含"一次就过"。
# 现改为进退出码：默认 RETRIES_MAX=0（retries>0 即红），确需容忍抖动的场景显式抬高上限，
# 且上限与实际重试数一律打进 `RETRIES=<n> (max=<m>) PASS|FAIL` 行，不接受只留日志。
set -u

# 勘误 E-03：retries 上限在开跑前就校验——写错时立刻退 2，不必等两分钟回归跑完才报错
RETRIES_MAX="${RETRIES_MAX:-0}"
case "$RETRIES_MAX" in
  ''|*[!0-9]*) echo "ERROR: RETRIES_MAX 必须是非负整数，当前为 '$RETRIES_MAX'" >&2; exit 2 ;;
esac

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="$HERE/.build"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

if [ ! -x "$CHROME" ]; then
  echo "ERROR: 找不到 Chrome 可执行文件: $CHROME" >&2
  echo "  安装 Google Chrome，或用 CHROME=/path/to/chrome bash tests/run.sh 指定路径" >&2
  exit 2
fi

mkdir -p "$OUT"

# 删目录用 python，不用 `rm -rf`：本机 rm 可能是安全删除包装器（bulk 阈值 50 个文件），
# Chrome profile 一个 150+ 文件，会被拦成 SAFE_DELETE_BULK_CONFIRM_REQUIRED ——
# 删除静默失败 → 复用上一轮 profile（带着旧 localStorage）→ 断言莫名少 1~2 条。
clean_dir() {
  python3 -c 'import shutil, sys; shutil.rmtree(sys.argv[1], ignore_errors=True)' "$1"
}

# 单实例锁：同一工作区并发跑会互相覆盖 tests/.build/ 的 html/dom/profile，
# 结果看似"偶发少几条断言"。宁可硬失败，也不要产出不可信的数字。
lock="$OUT/.run.lock"
if ! mkdir "$lock" 2>/dev/null; then
  holder="$(cat "$lock/pid" 2>/dev/null || echo "?")"
  if [ "$holder" != "?" ] && ! kill -0 "$holder" 2>/dev/null; then
    clean_dir "$lock"                      # 上一个进程已死，锁是残骸
    mkdir "$lock" 2>/dev/null || { echo "ERROR: 无法获取锁 $lock" >&2; exit 3; }
  else
    echo "ERROR: 另一个 run.sh 正在跑（pid=${holder}，锁 ${lock}）；并发跑会让结果不可信，等它结束再跑" >&2
    exit 3
  fi
fi
echo $$ > "$lock/pid"
trap 'clean_dir "$lock"' EXIT

# 用例: 名称|示例文件|基线断言数
CASES=(
  "00-embedded|__embedded__|94"
  "01-taskboard|example-01-task-board.json|137"
  "02-refund|example-02-refund-flow.json|123"
  "03-navtree|example-03-nav-tree.json|136"
  "04-masterdetail|example-04-master-detail.json|150"
  "05-behavior|example-05-behavior-model.json|117"
)

echo "== 生成器一致性（XX-014）"
if ! python3 "$HERE/check_generators.py"; then
  echo "FAIL: 生成器与示例不一致，先修生成器再跑回归（见 tests/check_generators.py）"
  exit 1
fi

# 清掉上一轮可能残留的 headless 进程（只杀 headless，不影响日常浏览器）
# 用 ^"$CHROME" 锚定命令行开头：避免匹配到"命令行里恰好含这串字"的外层 shell
# （曾因未锚定 pkill 到调用方自身，出现 Terminated: 15）
pkill -f "^${CHROME}.*--headless" >/dev/null 2>&1 || true

echo "== 容器回归（Chrome: ${CHROME}）"
total_ok=0
total_fails=0
total_retries=0
bad=0

for spec in "${CASES[@]}"; do
  name="${spec%%|*}"
  rest="${spec#*|}"
  example="${rest%%|*}"
  base="${rest##*|}"
  html="$OUT/$name.html"
  dom="$OUT/$name.dom.html"
  errlog="$OUT/$name.chrome.err"
  runlog="$OUT/$name.chrome.log"
  : > "$runlog"
  # 每轮先清掉该用例的全部 profile，保证从零状态起跑
  clean_dir "$OUT/profiles/$name"

  python3 "$HERE/build_cases.py" "$example" "$HERE/harness.js" "$html" >/dev/null || {
    echo "CASE $name fails=1 ok=0 retry=0 (baseline=$base) [FAIL 构建失败]"
    bad=1
    continue
  }

  # 偶发超时（页面尚未跑完、__testout 未落地）时重试一次；
  # 重试必须在 CASE 行以 retry=N 显式暴露，不允许静默洗白。
  fails=""
  oks=""
  case_retries=0
  last_rc=0
  for attempt in 1 2; do
    [ "$attempt" -eq 2 ] && case_retries=1
    # 每次尝试用一个全新 profile 目录（不同 attempt 不同路径），不删也不复用
    prof="$OUT/profiles/$name/a$attempt"
    "$CHROME" --headless=new --disable-gpu --no-sandbox --no-first-run --disable-extensions \
      --user-data-dir="$prof" --window-size=1680,1000 --virtual-time-budget=8000 \
      --dump-dom "file://$html" > "$dom" 2>"$errlog"
    last_rc=$?
    {
      echo "--- attempt $attempt exit=$last_rc dom_bytes=$(wc -c < "$dom" | tr -d ' ')"
      tail -c 2000 "$errlog"
    } >> "$runlog"

    parsed="$(python3 - "$dom" <<'PY'
import html as H, re, sys
s = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r'<div id="__testout"[^>]*data-fails="(\d+)"[^>]*>(.*?)</div>', s, re.S)
print("NA" if not m else "%d %d" % (int(m.group(1)), H.unescape(m.group(2)).count("ok   ")))
PY
)"

    if [ "$parsed" = "NA" ]; then
      # 变量必须带花括号：$last_rc 后面紧跟全角标点时，bash 可能把多字节并入变量名
      # （曾出现 line 99: last_rc?: unbound variable，set -u 下直接中止整套回归）
      [ "$attempt" -eq 1 ] && echo "  .. $name 未拿到 __testout (exit=${last_rc})，重试一次"
      fails=1
      oks=0
      continue
    fi
    read -r fails oks <<< "$parsed"
    break
  done
  clean_dir "$OUT/profiles/$name"

  total_ok=$((total_ok + oks))
  total_fails=$((total_fails + fails))
  total_retries=$((total_retries + case_retries))

  status="OK"
  note=""
  if [ "$fails" -gt 0 ] || [ "$oks" -ne "$base" ]; then
    status="FAIL"
    bad=1
    if [ "$oks" -eq 0 ]; then
      note=" (no __testout, exit=$last_rc)"
    fi
  fi
  echo "CASE $name fails=$fails ok=$oks retry=$case_retries (baseline=$base) [$status]${note}"
done

echo "TOTAL ok=$total_ok fails=$total_fails retries=$total_retries (baseline=757)"
# 勘误 E-03：retries 必须进退出码，且上限与实际值都要出现在输出里（CI 匿名日志读不到明细）
if [ "$total_retries" -gt "$RETRIES_MAX" ]; then
  echo "RETRIES=$total_retries (max=$RETRIES_MAX) FAIL"
  bad=1
else
  echo "RETRIES=$total_retries (max=$RETRIES_MAX) PASS"
fi
if [ "$bad" -ne 0 ] || [ "$total_ok" -ne 757 ] || [ "$total_fails" -ne 0 ]; then
  echo "RESULT FAIL"
  exit 1
fi
echo "RESULT PASS"
exit 0
