#!/usr/bin/env bash
# 容器回归：6 个用例（00-embedded + example-01~05），一条命令给出退出码。
# 用法:
#   bash tests/run.sh
#   CHROME=/path/to/chrome bash tests/run.sh
#   RETRIES_MAX=1 bash tests/run.sh      # 允许的重试上限（默认 0；勘误 E-03）
# 退出码:
#   0 = 6 用例全绿且断言数与基线一致，且 retries <= RETRIES_MAX（默认 0）
#   1 = 有失败（fails>0 或条数不等于基线，或生成器漂移，或 retries > RETRIES_MAX）
#   2 = 环境不可用（找不到 Chrome / $TMPDIR 不可写 / 清理失败）
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

# 删目录走 tests/clean_dir.py（XX-029），不用 `rm -rf`：本机 rm 可能是安全删除包装器
# （bulk 阈值 50 个文件），Chrome profile 一个 150+ 文件，会被拦成
# SAFE_DELETE_BULK_CONFIRM_REQUIRED。而原来那条 `shutil.rmtree(..., ignore_errors=True)`
# 把"删失败"降级成"无事发生"——删不掉和本来就没有长得一模一样，于是"这次跑的是不是
# 干净目录"变成不可观测变量，症状是"少几条断言"，人的第一反应是重跑一次。
# 现在：目录不存在 → 0；删完仍在 → 打印 CLEAN_FAILED=<路径> 并返回 2。
clean_dir() {
  python3 "$HERE/clean_dir.py" "$1"
}

# 单实例锁：同一工作区并发跑会互相覆盖 tests/.build/ 的 html/dom/profile，
# 结果看似"偶发少几条断言"。宁可硬失败，也不要产出不可信的数字。
lock="$OUT/.run.lock"
if ! mkdir "$lock" 2>/dev/null; then
  holder="$(cat "$lock/pid" 2>/dev/null || echo "?")"
  if [ "$holder" != "?" ] && ! kill -0 "$holder" 2>/dev/null; then
    # 上一个进程已死，锁是残骸 —— 删不掉说明前置条件不成立，宁可不跑
    clean_dir "$lock" || { echo "ERROR: 锁残骸删不掉，拒绝在不干净的状态下起跑：$lock" >&2; exit 2; }
    mkdir "$lock" 2>/dev/null || { echo "ERROR: 无法获取锁 $lock" >&2; exit 3; }
  else
    echo "ERROR: 另一个 run.sh 正在跑（pid=${holder}，锁 ${lock}）；并发跑会让结果不可信，等它结束再跑" >&2
    exit 3
  fi
fi
echo $$ > "$lock/pid"

# per-attempt 的 Chrome profile 一律放在**工作树之外**的临时目录：
#  1) 路径不在仓库内，删它不会被 safe-delete 当成"批量删除仓库文件"拦掉 ——
#     实测旧路径 tests/.build/profiles 的 clean_dir 一次都没删成功（954 个文件
#     / 13MB，跑完 6 个目录全在），而删除失败被 ignore_errors 吞掉；
#     后果是"跑前必须是干净的"变成隐性前提，第 2 次连跑就掉到 754/4（Chrome
#     复用带旧 localStorage 的 profile → hash 基线错误 / 状态覆写断言假红）。
#  2) 每次 run 一个 mktemp 目录，两次连跑天然互不污染；退出时整体清掉。
# **不要把这里改回 $OUT 下面的固定路径**：那等于把"上一轮残留"写进判据前提。
TMP_BASE="${TMPDIR:-/tmp}"
TMP_BASE="${TMP_BASE%/}"                   # macOS 的 TMPDIR 带尾斜杠，去掉免得路径出现 //
PROF_ROOT="$(mktemp -d "$TMP_BASE/xx-prd-profiles.XXXXXX" 2>/dev/null)"
if [ -z "$PROF_ROOT" ] || [ ! -d "$PROF_ROOT" ]; then
  # profile 建不出来 → 每个 CASE 都会在 Chrome 那一步以"没有 __testout"收场，
  # 症状是"断言少了几条"，而不是"环境不可用"。必须在这里就退 2。
  echo "ERROR: \$TMPDIR 不可写，mktemp -d 失败（TMPDIR=${TMPDIR:-<未设置>}，实际用 ${TMP_BASE}）" >&2
  clean_dir "$lock" || true
  rm -f "$lock/pid" 2>/dev/null || true
  exit 2
fi
echo "PROFILES_DIR=$PROF_ROOT"

# 收尾清理：失败只留痕（CLEAN_FAILED 会自己打出来），不 exit 非 0。
# **不收 `exit 2`**：这个函数由 trap EXIT 触发，里面的 exit 会覆盖被测命令的真实退出码，
# 把 757 的成功洗成 ENV、把 FAIL 也洗成 ENV —— 那比不清理更坏，因为它给了一个假结论。
# 验收要用「业务全过 + 清理必失败」锁住 rc 仍为 0（XX-029 acceptance 6）。
cleanup() {
  clean_dir "$lock" || true
  # $PROF_ROOT 在 mktemp 失败时是空串，而空串传给 clean_dir 会被解析成当前目录 `.`
  # —— 那一步就删到工作树上了。所以非空才清。
  [ -n "$PROF_ROOT" ] && { clean_dir "$PROF_ROOT" || true; }
  return 0
}
trap cleanup EXIT

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
  # 每轮先清掉该用例的全部 profile，保证从零状态起跑。
  # 删不掉就停在这里（退出码 2，且此前不会有任何 CASE 行）——放它过去的话，
  # 结果是"757 变成 755"这种伪装成断言失败的形态，比直接 ENV 难查得多。
  clean_dir "$PROF_ROOT/$name" || {
    echo "ERROR: profile 目录删不掉，拒绝在不干净的状态下起跑：$PROF_ROOT/$name" >&2
    exit 2
  }

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
    prof="$PROF_ROOT/$name/a$attempt"
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
  clean_dir "$PROF_ROOT/$name" || true

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
