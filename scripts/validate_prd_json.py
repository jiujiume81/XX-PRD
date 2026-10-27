#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_prd_json.py — XX-PRD 产物结构校验器

用法:
    python3 validate_prd_json.py <file.json|file.html> [more...]
    python3 validate_prd_json.py --json      # 机器可读输出
    python3 validate_prd_json.py --profile=delivery <file...>   # 交付档（XX-021）

校验维度:
  1. 顶层结构完整性
  2. ID 唯一性与前缀规范
  3. 引用完整性（悬空引用检测）
  4. 组件类型白名单
  5. 页面状态覆盖（默认/加载/空/异常 四态）
  6. EARS 质量门禁
  7. 状态机完整性（初始态 / 孤立状态）
  8. 标注闭环
  9. 布局与交互完整性
 10. 数据模型（实体 / 字段 / 关系 / 派生字段）
 11. 行为建模：capabilities（角色 × 状态 × 命令）与状态转移覆盖
 12. 页面职责契约（页面切分、命令归属唯一性、多功能混页提示）
 13. 交付档（--profile=delivery，XX-021）：tasks / capabilities / pages[].contract
     缺失即 ERROR；transitions[].ui（XX-019）与 requirement.ui（XX-020）必填。
     默认档把「缺失」降为 WARN，但「指向不存在的交互」两档都 ERROR。
     requirement.ui 与 transitions[].ui 同构，三选一：
       {"interactionId": "ix-xxx"} / {"kind": "system"} / {"kind": "page-enter"}
 14. 需求级前置/后置（XX-023）：guards[] / effects[] 是**可选**字段，但写了就必须写对 ——
     guards[].kind 只有 block/warn，text 不得为空，整体必须是数组；effects[].text 必填。
     缺失不报（存量产物没有它）。条数单独打在 `行为补充：guards=N effects=M` 这行：
     "字段存在"和"里面有几条"是两件事，只报前者的话，guards:[] 与 7 条像话的守卫看不出差别。

退出码: 0 = 无 ERROR, 1 = 存在 ERROR
"""
import json
import re
import sys
import os
import hashlib

# ---------- 组件类型白名单（与 references/05-component-states.md 保持一致） ----------
WHITELIST = {
    # 布局
    "Layout", "Header", "Sider", "Content", "Footer", "Row", "Col", "Space", "Divider",
    # 导航
    "Menu", "Breadcrumb", "Tabs", "Steps", "Pagination", "Dropdown", "Segmented",
    # 数据录入
    "Button", "Input", "TextArea", "InputNumber", "Select", "Checkbox", "CheckboxGroup",
    "Radio", "RadioGroup", "Switch", "DatePicker", "TimePicker", "Upload", "Form",
    "FormItem", "Slider", "Rate", "Cascader", "Transfer",
    # 数据展示
    "Table", "List", "List.Item", "Card", "Descriptions", "Tag", "Badge", "Avatar",
    "Tooltip", "Collapse", "Timeline", "Tree", "Statistic", "Empty", "Progress",
    "Skeleton", "Alert", "Image", "Carousel", "Calendar",
    # 复合结构（主子表：主表 + 可展开子表）
    "MasterDetail",
    # 反馈
    "Modal", "Drawer", "Popconfirm", "Spin", "Result",
    # 排版与辅助
    "Typography", "Paragraph", "Text", "Icon", "Placeholder", "Chart", "Frame",
}

ID_PREFIXES = {
    "u-": "user", "m-": "module", "page-": "page", "flow-": "userFlow",
    "n-": "componentTreeNode", "ix-": "interaction", "s-": "pageState",
    "an-": "annotation", "c-": "component", "sm-": "stateMachine",
    "REQ-": "requirement", "bp-": "boardPlan", "q-": "openQuestion",
    "cap-": "capability", "task-": "task",
}

# ---------- 行为建模（见 references/09-behavior-model.md） ----------
CAP_POLICIES = {"hidden", "disabled", "reject"}
CAP_REQUIRED = ("id", "name", "entity", "actor", "from", "policy")
# 「用户看到什么」的兜底文案：不可用原因不能是空话
CAP_VAGUE_REASONS = {"不允许", "状态不允许", "无权限", "不能操作", "不可用", "错误", "失败"}
# 拒绝/不可用的语义关键词（用于检查验收条件是否覆盖非法路径）
DENIAL_WORDS = ("不可", "不能", "禁止", "拒绝", "无权限", "越权", "置灰", "隐藏", "不允许", "失败")

# 页面职责（见 references/10-page-decomposition.md）
CONTRACT_REQUIRED = ("task", "actor", "entity", "owns")

# ---------- 校验档位（XX-021） ----------
# default  ：宽松档。结构错才 ERROR，新增的语义闭合检查一律 WARN —— 存量 PRD 不会被一夜判红。
# delivery ：交付档。交付前必须闭合的检查升 ERROR 并让退出码非 0：
#            tasks / capabilities / pages[].contract 缺失（XX-021）、
#            人工转移缺 ui（XX-019）、需求缺 ui（XX-020）。
#            存在的意义不是「更啰嗦」，而是让「页面层没落地」这件事无法靠 errors=0 蒙过去。
PROFILES = ("default", "delivery")


EARS_PATTERNS = {"ubiquitous", "event-driven", "state-driven", "option", "unwanted"}

SUBJECTIVE_WORDS = ["友好", "快速", "合理", "尽量", "美观", "尽可能", "优秀", "良好",
                    "适当", "较好", "高效", "便捷", "流畅"]

IMPL_HINTS = ["api/", "/api", "数据库", "表名", "接口路径", "SELECT ", "INSERT ",
              "React", "Vue", "Django", "Spring", "调用接口"]

BOARD_STATUS = {"todo", "doing", "done"}
ANNO_STATUS = {"open", "resolved", "rejected"}
REQ_STATUS = {"draft", "confirmed"}
REQ_SOURCE = {"user", "demo", "inferred"}

# 节点级允许的字段（其余应写进 props）
NODE_KEYS = {"id", "type", "ref", "props", "state", "when", "children", "slots"}

# interactions.actions 的 action 白名单（必须与容器 doAction 的 case 分支一致）
ACTION_WHITELIST = {
    "setState", "setNode", "gotoState", "navigate", "back", "scrollTo",
    "message", "showModal", "showDrawer", "hideModal", "hideDrawer",
    "delay", "reset",
}
# 事件白名单
EVENT_WHITELIST = {"click", "change", "submit", "focus", "blur", "hover"}

# 四态关键字（中文/英文都接受）
STATE_KEYS = {
    "default": ["默认", "default", "常规", "正常"],
    "loading": ["加载", "loading", "请求中"],
    "empty": ["空", "empty", "无数据"],
    "error": ["异常", "错误", "error", "失败", "无权限", "超时"],
}


class Report:
    def __init__(self, target, profile="default"):
        self.target = target
        self.profile = profile
        self.errors = []
        self.warns = []
        self.infos = []
        # 第三种状态：判据在，但产物里没有可判的输入。
        # 它既不是 PASS（会得到"全绿"的假象）也不是 ERROR（会把"没写输入"和"写错了"混成一件事）。
        # 与 check_ui_shape 的 INCOMPLETE 同义（见 references/13 §5 的落地状态行）。
        self.incomplete_msgs = []
        # R1–R4 的逐条状态：[(rid, "PASS"/"ERROR"/"INCOMPLETE"/"WARN")]，供自证脚本按 rid 断言。
        self.r_group = []
        # SS-01 的 INCOMPLETE 是**工具链缺失**（契约文件没有 / 与容器不同步），
        # 不是产物的错：不修就没法判，所以任何档都要非 0 退出（XX-050 裁定）。
        self.toolchain_fail = False

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warns.append(msg)

    def info(self, msg):
        self.infos.append(msg)

    def incomplete(self, msg):
        self.incomplete_msgs.append(msg)


# ---------- 载入 ----------
def load_data(path):
    """支持 .json 与 .html（从 #iprd-data 提取）。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    if path.lower().endswith((".html", ".htm")):
        m = re.search(
            r'<script[^>]*id=["\']iprd-data["\'][^>]*>(.*?)</script>', raw, re.S)
        if not m:
            raise ValueError("HTML 中未找到 <script id=\"iprd-data\"> 数据块")
        raw = m.group(1)
    return json.loads(raw)


# ---------- 工具 ----------
def walk_nodes(node, out):
    if not isinstance(node, dict):
        return
    if node.get("id"):
        out.append(node)
    for c in node.get("children") or []:
        walk_nodes(c, out)
    for key, arr in (node.get("slots") or {}).items():
        for c in arr or []:
            walk_nodes(c, out)
    # 列表页「三件套」里的按钮也是可寻址节点（容器会给它们挂 data-node-id）。
    # 注意：toolbar / queryActions 的条目有两种写法 ——
    #   ① 节点式 {id, type:"Button", props:{...}}
    #   ② 属性式 {id, type:"primary", text:"新建"}（type 是按钮视觉类型，不是组件类型）
    # 只有 type 命中组件白名单时才当节点递归，否则会把 "primary" 误判成组件类型。
    pr = node.get("props") or {}
    for key in ("toolbar", "queryActions"):
        for it in pr.get(key) or []:
            if isinstance(it, dict) and it.get("id") and it.get("type") in WHITELIST:
                walk_nodes(it, out)


def collect_node_ids(data):
    ids = set()
    for page in data.get("pages") or []:
        nodes = []
        walk_nodes(page.get("componentTree") or {}, nodes)
        for n in nodes:
            ids.add(n["id"])
            # 属性式 toolbar/queryActions 条目（{id,type:"primary",text}）也是可寻址节点
            for it in toolbar_items(n):
                ids.add(it["id"])
            # 筛选区渲染器打在按钮上的 id（queryId / resetId），同族
            for iid in filter_button_ids(n):
                ids.add(iid)
    return ids


def toolbar_items(node):
    """列表页三件套里「属性式」的按钮条目（type 是视觉类型而非组件类型）。"""
    pr = node.get("props") or {}
    out = []
    for key in ("toolbar", "queryActions"):
        for it in pr.get(key) or []:
            if isinstance(it, dict) and it.get("id") and it.get("type") not in WHITELIST:
                out.append(it)
    return out


# ---------- 筛选区按钮的「合成 id」（REQ-I07-07 / I-07 需求单 §4 第 1 条） ----------
# 容器 buildFilterBar 在 `filterBar:'grid3'` 且 `query` 非空时渲染「重置 → 查询」两个动作按钮，
# 并把 props.resetId / props.queryId 打到按钮的 data-node-id 上。也就是说按钮**确实存在**，
# 只是它没有独立的组件树节点 —— 与 toolbar / queryActions 的「属性式条目」是同一族。
#
# 这是**结构性接入**，不是白名单：白名单会把「按钮画不出来」这件事合法化；这里只是承认
# 「容器生成的按钮也是可寻址节点」。所以必须配一条反向校验：声明了 id 而渲染器不会生成
# 该按钮（无 query 字段 / 走的还是旧 query 条）时报 ERROR —— 只认 id 不验存在就是放宽。
FILTER_SYNTH_KEYS = ("queryId", "resetId")


def filter_button_ids(node):
    """渲染器真的会打上 data-node-id 的筛选按钮 id（列表见上）。"""
    if node.get("type") != "Table":
        return []
    pr = node.get("props") or {}
    if not (pr.get("query") or []) or pr.get("filterBar") != "grid3":
        return []
    return [pr[k] for k in FILTER_SYNTH_KEYS if pr.get(k)]


def filter_ids_not_rendered(node):
    """声明了、但渲染器不会生成的筛选按钮 id（用于反向报错）。"""
    if node.get("type") != "Table":
        return []
    pr = node.get("props") or {}
    rendered = set(filter_button_ids(node))
    return [(k, pr[k]) for k in FILTER_SYNTH_KEYS if pr.get(k) and pr[k] not in rendered]


# 容器为某些组件内建了「合成节点 id」，可被 interactions.on.target / actions.scrollTo 引用：
#   <Header 节点 id>__back            → 返回箭头（内建 back 动作）
#   <Modal 节点 id>__ok / __cancel    → 弹窗底部「确定」/「取消」按钮
#   <Table 节点 id>__row_<i>          → 第 i 行（需 props.rowClick: true）
#   <Table 节点 id>__act_<i>_<key>    → 第 i 行操作列的第 key 个按钮
# 序号位可写成 `*` 作为通配（一条 interaction 服务所有行 / 所有行内按钮）：
#   <Table 节点 id>__row_*            → 任意一行
#   <Table 节点 id>__act_*_<key>      → 任意一行的第 key 个按钮
SYNTH_RE = re.compile(r"^(.+?)__(back|ok|cancel|row_(?:\d+|\*)|act_(?:\d+|\*)_[A-Za-z0-9_\-*]+)$")


def collect_node_types(data):
    types = {}
    for page in data.get("pages") or []:
        nodes = []
        walk_nodes(page.get("componentTree") or {}, nodes)
        for n in nodes:
            types[n["id"]] = n.get("type")
            for it in toolbar_items(n):
                types.setdefault(it["id"], "Button")
    return types


def node_subtree(node):
    """收集某节点自身及其全部后代（含 slots）。"""
    out = []
    walk_nodes(node, out)
    return out


def walk_nodes_skip(node, out, skip_types=()):
    """同 walk_nodes，但整棵跳过指定类型的子树（例如 MasterDetail 内部的子表不算「本页第二张表」）。"""
    if not isinstance(node, dict):
        return
    if node.get("type") in skip_types:
        return
    if node.get("id"):
        out.append(node)
    for c in node.get("children") or []:
        walk_nodes_skip(c, out, skip_types)
    for _, arr in (node.get("slots") or {}).items():
        for c in arr or []:
            walk_nodes_skip(c, out, skip_types)


# ---------- 容器选型准则（见 references/08-container-choice.md） ----------
# 只数「叶子字段控件」，FormItem 只是包裹层，不重复计数
FIELD_TYPES = {"Input", "TextArea", "InputNumber", "Select", "Checkbox", "CheckboxGroup",
               "Radio", "RadioGroup", "Switch", "DatePicker", "TimePicker", "Upload",
               "Slider", "Rate", "Cascader", "Transfer"}
MODAL_MAX_FIELDS = 15        # 长表单（>15 字段）禁用对话框
MODAL_DETAIL_HINT_FIELDS = 8  # 弹窗里塞这么多字段的「详情」通常展不开关联信息


def resolve_target(tgt, node_types):
    """解析交互目标：真实节点 / 容器合成节点（支持 `*` 通配）。返回 None 表示合法，否则返回错误说明。"""
    if not tgt:
        return None
    if tgt in node_types:
        return None
    m = SYNTH_RE.match(tgt)
    if not m:
        return f"节点 `{tgt}` 不存在"
    base, kind = m.group(1), m.group(2)
    if base not in node_types:
        return f"合成目标 `{tgt}` 的基节点 `{base}` 不存在"
    btype = node_types.get(base)
    if kind == "back":
        if btype != "Header":
            return f"合成目标 `{tgt}`：`__back` 只能挂在 Header 上，`{base}` 是 {btype}"
    elif kind in ("ok", "cancel"):
        if btype != "Modal":
            return f"合成目标 `{tgt}`：`__{kind}` 只能挂在 Modal 上，`{base}` 是 {btype}"
    elif btype != "Table":
        return f"合成目标 `{tgt}`：`{kind.split('_')[0]}` 只能挂在 Table 上，`{base}` 是 {btype}"
    return None


def eval_pattern_trigger_ok(pat, trigger):
    """pattern 与 trigger 的填写一致性。"""
    if pat == "ubiquitous":
        return not trigger
    return True


def ui_kind_is_system(ui):
    """`ui` 是否声明为「系统自动流转」：`{"kind": "system"}`。

    requirement.ui 与 transitions[].ui 共用这一个判断 —— 两处的 system 语义必须同源，
    否则「什么算系统行为」会在两个检查里各长一套，迟早打架。
    """
    return isinstance(ui, dict) and ui.get("kind") == "system"


def transition_is_system(t):
    """这条转移是不是「系统自动触发」。三种写法等价，任一成立即算：
      - `"system": true`（老写法；`tests/check_generators.py` 的 `count_system()`
        数的就是它 —— 注意在 tests/ 不在 scripts/，别按名字去 scripts/ 找）
      - `"role": "system"`
      - `"ui": {"kind": "system"}`（XX-019 的新写法）
    判成系统转移的，不要求写 pageId / interactionId —— 它没有按钮可点。
    """
    return (t.get("system") is True
            or t.get("role") == "system"
            or ui_kind_is_system(t.get("ui")))


def interaction_ids_of(page):
    return {ix.get("id") for ix in (page or {}).get("interactions") or []}


# ---------- SS-01：props 消费闭合（I-11 / XX-050） ----------
# 来历：容器逐字段手写读 props（`p.xxx`），没有整包透传。产物里写一个容器没读的键
# = 写了不生效，而且不报任何错；几何判据（check_ui_shape）只量像素，对这类键完全免疫。
# 所以从**声明侧**判，白名单由 scripts/props_contract.py 从容器源码机械提取。
#
# 判定口径（references/04 §6.8.4）：
#   PASS        每个 (type,key) 都在「该 type 可读集 ∪ shared 通用键」里
#   ERROR       越界。**不设 WARN**：「键被别的类型读过」不是作者的处境差异，
#               是这个键写错了节点 —— 判成 WARN 就是假绿（example-06 的 Alert.text
#               在 WARN 口径下退出码是 0，而画面是两条空白告警条）
#   INCOMPLETE  契约缺失 / 无法解析 / 与容器源码逐类型比对不一致 / 产物里一个节点级
#               props 都没有。前三种是**工具链缺失**，任何档都非 0。
#
# 同步判据用「运行时重算 byType 与服务端比对」，不用整文件 sha：
# sha 对「改一行注释」过敏（全线 INCOMPLETE），对「清单换格式」失明。
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
_PROPS_CONTRACT = os.path.join(_ROOT, "assets", "container", "props-contract.json")
_CONTAINER_HTML = os.path.join(_ROOT, "assets", "container", "index.html")
_PROPS_UNSUPPORTED = os.path.join(_ROOT, "references", "props-unsupported.json")

# 值域也是一部分契约（R5）：写了合法键、给了非法值，同样是「声明不生效」。
_VALUE_DOMAIN = [
    ("Drawer", "placement", ("right", "left", "top", "bottom"), "right/left/top/bottom 四值"),
    ("*", "visible", (True, False), "布尔"),
]

# R6（Drawer 声明宽度必须等于渲染）：容器只有两档 —— 不写/写不出数值时 CSS 默认 420，
# >=560 进 `.ant-drawer.w-lg` 的 560，其余正数写 inline（等于声明）。
_DRAWER_W_LG = 560
_DRAWER_W_DEFAULT = 420


def _js_number(v):
    """`Number(v)` 的 JSON 子集。返回 float；NaN/不可解析返回 None（与 isFinite 取反对应）。

    别用 `float(v)` 代替：`float("")` 抛异常（JS 是 0）、`float(True)` 得 1.0（JS 也是 1，
    但语义上那是布尔不是宽度 —— 交给调用方按 None 之外的路径判）。
    """
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return None if v != v else float(v)          # v != v 即 NaN
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return 0.0
        try:
            n = float(s)
        except ValueError:
            return None
        return None if n != n else n
    return None


def _drawer_rendered_width(pr):
    """照 `R.Drawer` 的取宽逻辑算**实际渲染宽度**（px）。返回 None 表示「满宽」。

    只是把容器那两行翻译成 Python，不新增口径：
      - `horiz`（top/bottom）时既不进 w-lg 也不写 inline → 满宽
      - `isFinite(w)&&w>=560&&!authored` → `.ant-drawer.w-lg` 的 560
      - `isFinite(w)&&w>0&&!lg&&!(authored&&w===560)` → inline，等于声明
      - 其余 → `.ant-drawer` 的 CSS 默认 420（或作者自己 class 带的 w-lg）
    """
    place = pr.get("placement")
    if place not in ("right", "left", "top", "bottom"):
        place = "right"                              # 写错时容器按 right 处理（另由 R5 判）
    if place in ("top", "bottom"):
        return None
    w = _js_number(pr.get("width"))
    authored = "w-lg" in str(pr.get("class") or pr.get("className") or "")
    base = _DRAWER_W_LG if authored else _DRAWER_W_DEFAULT
    if w is not None and w >= _DRAWER_W_LG and not authored:
        return _DRAWER_W_LG
    if w is not None and w > 0 and not (authored and w == _DRAWER_W_LG):
        return w
    return base


def _drawer_width_issues(pid2, label, t, pr):
    """R6 三条：`top|bottom` 不吃 width / width 必须能取成数 / 只有 420·560 两档。

    判据只有一句：**声明必须等于渲染**。所以它天然不会误杀 440 / 520（inline 写多少渲多少），
    也不会误杀「作者自己 class 带 w-lg 且声明 600」那种真能渲成 600 的写法。
    消息一律写成「声明 X、渲成 Y」—— 写「取值非法」会把作者赶去找枚举表，而这里没有枚举。
    """
    if t != "Drawer" or "width" not in pr:
        return []
    raw = pr.get("width")
    place = pr.get("placement")
    rendered = _drawer_rendered_width(pr)
    if rendered is None:
        if place not in ("top", "bottom"):
            return []
        return ["%s `%s`(Drawer).props.width = %r 配 placement=%r（声明 %r，**渲成满宽** —— "
                "top/bottom 抽屉不吃 width：R.Drawer 里 horiz 为真时既不加 w-lg 也不写 inline）；"
                "删掉 width" % (pid2, label, raw, place, raw)]
    decl = _js_number(raw)
    if decl is not None and decl == rendered:
        return []
    where = "%s `%s`(Drawer).props.width = %r（声明 %r，渲成 %s" % (
        pid2, label, raw, raw, ("%gpx" % rendered))
    if decl is None:
        hint = ("R.Drawer 用 Number(p.width) 取宽，非数字得 NaN，inline 不生效、"
                "回落 .ant-drawer 默认 %dpx）；改成纯数字，如 width: 520" % _DRAWER_W_DEFAULT)
    elif decl <= 0:
        hint = ("inline 只在 w>0 时写，0/负数回落默认 %dpx）；改成正数，或直接删掉 width"
                % _DRAWER_W_DEFAULT)
    else:
        hint = ("isFinite(w)&&w>=560 一律进 .ant-drawer.w-lg，CSS 只有 %dpx 这一档，"
                "更宽的声明会被压平）；改写成 %d，或把档位缺口单独立项改容器"
                % (_DRAWER_W_LG, _DRAWER_W_LG))
    return [where + "，" + hint]


def _sha256_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _load_props_contract(rep):
    """读契约并**运行时重算**比对。返回契约 dict；判不了时返回 None（已记 INCOMPLETE）。"""
    if not os.path.exists(_PROPS_CONTRACT):
        rep.incomplete("[SS-01] props 契约文件缺失（先跑 python3 scripts/props_contract.py）")
        rep.toolchain_fail = True
        return None
    try:
        with open(_PROPS_CONTRACT, encoding="utf-8") as f:
            c = json.load(f)
    except Exception as e:
        rep.incomplete("[SS-01] props 契约文件无法解析：%s" % e)
        rep.toolchain_fail = True
        return None
    if not os.path.exists(_CONTAINER_HTML):
        rep.incomplete("[SS-01] 找不到容器源码 %s，无法校验契约是否过期" % _CONTAINER_HTML)
        rep.toolchain_fail = True
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_props_contract", os.path.join(_SCRIPTS, "props_contract.py"))
        pc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pc)
        with open(_CONTAINER_HTML, encoding="utf-8") as f:
            cur = pc.extract(f.read())
    except Exception as e:
        rep.incomplete("[SS-01] 重算契约失败（生成器不可用）：%s" % e)
        rep.toolchain_fail = True
        return None

    diffs = []
    # 两枚哈希都要对（§6.8.3）：容器改了没重生成、或**不支持清单**改了没重生成，都是过期契约。
    # 清单没有逐键比对可做（它是理由表，不进 byType），只校容器会漏掉「过期理由表」。
    for field, path, human in (
            ("sourceSha256", _CONTAINER_HTML, "容器"),
            ("unsupportedSha256", _PROPS_UNSUPPORTED, "不支持清单")):
        want = _sha256_file(path)
        got = c.get(field)
        if want is None:
            diffs.append("找不到%s源文件 %s，无法校验契约是否过期" % (human, path))
        elif not got:
            diffs.append("契约缺 %s（旧版契约，重跑生成器）" % field)
        elif got != want:
            diffs.append("%s sha：契约 %s / 现文件 %s" % (human, got[:12], want[:12]))
    if c.get("renderers") != cur["rendererCount"]:
        diffs.append("渲染器数：契约 %s / 源码 %s" % (c.get("renderers"), cur["rendererCount"]))
    if sorted(c.get("shared") or []) != sorted(cur["shared"]):
        diffs.append("shared：契约 %s / 源码 %s" % (c.get("shared"), cur["shared"]))
    cb = {k: set(v) for k, v in (c.get("byType") or {}).items()}
    nb = {k: set(v) for k, v in cur["byType"].items()}
    for t in sorted(set(cb) | set(nb)):
        if cb.get(t, set()) != nb.get(t, set()):
            diffs.append("%s：源码多 %s / 契约多 %s"
                         % (t, sorted(nb.get(t, set()) - cb.get(t, set())) or "-",
                            sorted(cb.get(t, set()) - nb.get(t, set())) or "-"))
    if diffs:
        rep.incomplete("[SS-01] props 契约与源文件不一致（%d 处）—— 先跑 "
                       "python3 scripts/props_contract.py：%s%s"
                       % (len(diffs), "；".join(diffs[:5]), " 等" if len(diffs) > 5 else ""))
        rep.toolchain_fail = True
        return None
    return c


def _iter_prop_nodes(node, path, page_id):
    """遍历节点级 props 与插槽名，**包含没有 id 的模板节点**。

    没有 id 不等于不在范围内：example-02 的 `List.Item` 就没有 id，
    按 id 过滤会让整类模板静默漏检（假绿）。

    产出 `(page_id, label, type, props, slot_names)`：插槽名要单独判（R2 按 type 判），
    不能只靠 props 的键 —— 容器对没读过的插槽是**静默丢弃**，画面不报错。
    """
    if not isinstance(node, dict):
        return
    t = node.get("type")
    label = node.get("id") or path
    pr = node.get("props")
    slots = sorted((node.get("slots") or {}).keys())
    if t and (isinstance(pr, dict) or slots):
        yield page_id, label, t, pr if isinstance(pr, dict) else {}, slots
    for i, c in enumerate(node.get("children") or []):
        for x in _iter_prop_nodes(c, "%s.children[%d]" % (label, i), page_id):
            yield x
    for k, arr in (node.get("slots") or {}).items():
        for i, c in enumerate(arr or []):
            for x in _iter_prop_nodes(c, "%s.slots.%s[%d]" % (label, k, i), page_id):
                yield x
    pr = pr if isinstance(pr, dict) else {}
    # 列表页「三件套」：toolbar / queryActions 的节点式条目（属性式条目 type 是视觉类型，跳过）
    for key in ("toolbar", "queryActions"):
        for i, it in enumerate(pr.get(key) or []):
            if isinstance(it, dict) and it.get("type") in WHITELIST:
                for x in _iter_prop_nodes(it, "%s.props.%s[%d]" % (label, key, i), page_id):
                    yield x
    # renderItem 模板：模板里的节点模板同样是节点，计入分母并受 R1–R6 约束。
    # 只做「遍历 + 路径带类型段」；R7 的细则（同类型兄弟靠 children[k]、节点级
    # renderItem 判 ERROR、无 id 寻址）留给 XX-054 —— 那几条改的是判据，不是分母。
    ri = pr.get("renderItem")
    if isinstance(ri, dict) and ri.get("type"):
        for x in _iter_prop_nodes(ri, "%s.props.renderItem(%s)" % (label, ri["type"]), page_id):
            yield x


def _more_samples(samples, limit=3):
    """同一个键还出现在哪些节点 —— 只报一处会让人修一轮冒一批。"""
    uniq, seen = [], set()
    for s in samples:
        if s in seen:
            continue
        seen.add(s)
        uniq.append(s)
    if len(uniq) <= 1:
        return ""
    return "（同键共 %d 处：%s%s）" % (len(uniq), "、".join(uniq[:limit]), "等" if len(uniq) > limit else "")


def check_props_contract(data, rep):
    """SS-01：每个节点 `props` 下的键，必须被容器**该类型**（或 shared 通用处理）读过。"""
    c = _load_props_contract(rep)
    if c is None:
        return

    by_type = {k: set(v) for k, v in (c.get("byType") or {}).items()}
    slots_by_type = {k: set(v) for k, v in (c.get("slotsByType") or {}).items()}
    shared = set(c.get("shared") or [])
    index = c.get("unsupportedIndex") or {}

    pairs = {}   # (type, key) -> [样例标签]
    bad_values = []
    bad_render = []   # R6：声明宽度与渲染宽度对不上
    bad_slots = []    # R2：插槽名按 type 判
    occ = 0
    for page in data.get("pages") or []:
        pid = page.get("id")
        for pid2, label, t, pr, slot_names in _iter_prop_nodes(page.get("componentTree") or {}, "componentTree", pid):
            for k, v in pr.items():
                occ += 1
                pairs.setdefault((t, k), []).append("%s `%s`(%s).props.%s" % (pid2, label, t, k))
                for dom_t, dom_k, allowed, human in _VALUE_DOMAIN:
                    if dom_k != k or dom_t not in ("*", t):
                        continue
                    ok = (isinstance(v, bool) if allowed == (True, False) else v in allowed)
                    if not ok:
                        bad_values.append("%s `%s`(%s).props.%s = %r（只能是 %s）"
                                          % (pid2, label, t, k, v, human))
            bad_render.extend(_drawer_width_issues(pid2, label, t, pr))
            for sk in slot_names:
                if sk in slots_by_type.get(t, ()):
                    continue
                have = sorted(slots_by_type.get(t) or [])
                bad_slots.append(
                    "%s `%s`(%s).slots.%s ← %s：%s"
                    % (pid2, label, t, sk, t,
                       ("只读 %s" % "/".join(have)) if have
                       else "**一个插槽都不读**（正文放 children；其它内容用 prop 表达）"))
    if not pairs and not bad_slots and not bad_render:
        rep.info("SS-01 props 消费闭合：INCOMPLETE（产物里没有任何节点级 props，无从判）")
        return

    bad = []
    for (t, k), samples in sorted(pairs.items()):
        if k in shared:
            continue
        if k not in by_type.get(t, set()):
            bad.append((t, k, samples))

    head = ("props 消费闭合（契约 %d 键 / %d 渲染器 / shared=%s）："
            "分母 %d 个 type×key（来源 %d 处出现）"
            % (len(c.get("allKeys") or []), c.get("renderers"),
               ",".join(sorted(shared)) or "-", len(pairs), occ))

    if bad or bad_values or bad_render or bad_slots:
        lines = []
        for t, k, samples in bad[:40]:
            u = index.get("%s.%s" % (t, k)) or index.get("*.%s" % k)
            if u:
                lines.append("%s ← 容器明确不支持：%s 替代：%s%s"
                             % (samples[0], u["why"], u["instead"], _more_samples(samples)))
            else:
                lines.append("%s ← 容器源码 0 命中%s" % (samples[0], _more_samples(samples)))
        if len(bad) > 40:
            lines.append("…另有 %d 个 type×key 越界未列出" % (len(bad) - 40))
        lines.extend(bad_slots[:10])
        lines.extend(bad_values[:10])
        lines.extend(bad_render[:10])
        # 尾句必须分得清四件事：键没人读 / 插槽没人读 / 枚举值写错 / 声明与渲染不符。
        # 最后一种如果混进「取值非法」，作者会去找一张并不存在的枚举表（R6 没有枚举，只有档位）。
        parts = []
        if bad:
            parts.append("**%d 个键容器不读**" % len(bad))
        if bad_slots:
            parts.append("%d 个插槽该类型不读" % len(bad_slots))
        if bad_values:
            parts.append("%d 处取值非法" % len(bad_values))
        if bad_render:
            parts.append("%d 处声明宽度与渲染不符" % len(bad_render))
        tail = parts[0]
        for p in parts[1:]:
            tail += "；另有 " + p
        rep.error(head + "｜" + tail + "：" + "；".join(lines))
    else:
        rep.info(head + "｜全部被容器读取")


# ---------- 校验主体 ----------
# ==================== 需求准确性 R1–R4（references/13-requirements-accuracy.md） ====================
# 本节只放"与数据结构无关"的取数工具；判定写在 validate() 里，与其它规则共用 gate() 的档位语义。
R2_TRIGGERS = ("分发至", "各负责人", "多个", "分别", "每个", "明细", "两种")


def _r_core(name):
    """字段名去掉括注：'我的任务（各负责人待办入口）' → '我的任务'。
    R1-b 要匹配的是核心词 —— 括注是给人看的解释，渲染文本里通常没有。"""
    return re.split(r"[（(]", name or "", 1)[0].strip()


def _r_page_index(page):
    """返回 (节点 id 集合, {节点 id: 该节点可渲染文本})。

    可渲染文本**只取用户看得见的那些位置**：props 的
    text/title/label/content/placeholder/extra/value/description、Table 的 columns[].title、
    以及 children 里的裸字符串。**不做全文搜索** —— 13 §1.5 反模式 1 已经证伪过：
    `根本原因` 在 CAPA 产物里命中 1 次，命中的是测试数据的**值**，主表根本没有这个字段。
    """
    ids, texts = set(), {}

    def rec(n):
        if not isinstance(n, dict):
            return
        nid = n.get("id")
        buf = []
        pr = n.get("props") or {}
        for k in ("text", "title", "label", "content", "placeholder", "extra", "value",
                  "description", "detailTitle"):
            v = pr.get(k)
            if isinstance(v, str):
                buf.append(v)
        for col in (pr.get("columns") or []):
            if isinstance(col, dict) and isinstance(col.get("title"), str):
                buf.append(col["title"])
        for ch in (n.get("children") or []):
            if isinstance(ch, str):
                buf.append(ch)
        if nid:
            ids.add(nid)
            texts[nid] = "\n".join(buf)
        for ch in (n.get("children") or []):
            if isinstance(ch, dict):
                rec(ch)
        for sl in (n.get("slots") or {}).values():
            for ch in (sl if isinstance(sl, list) else [sl]):
                if isinstance(ch, dict):
                    rec(ch)

    tree = page.get("componentTree")
    for n in (tree if isinstance(tree, list) else [tree]):
        rec(n)
    # 13 R1-a 允许落位到 interactions 的 on.target —— 它也是"该页里真实存在的节点"
    for ix in (page.get("interactions") or []):
        tgt = ((ix.get("on") or {}).get("target"))
        if tgt:
            ids.add(tgt)
    return ids, texts


def _r_source_terms(data, target):
    """源文档点名词清单。两级来源，任取其一；都没有返回 None。

    ① 顶层 `sourceTerms[]`（内联，随产物走 —— 交付包是单文件，`shaping/` 不跟包）；
    ② `<产物目录>/shaping/source-terms.json`（阶段② 的落盘位置，13 §1.4）。
    返回 None 时 R1-c 与 R2 **不许**判 PASS：分母为 0 时「登记数 ≥ 0」恒成立，那是恒真式。
    """
    inline = data.get("sourceTerms")
    if isinstance(inline, list) and inline:
        out = []
        for x in inline:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict):
                out.append(x.get("name") or x.get("term") or "")
        return [x for x in out if x]
    if target and os.path.exists(target):
        cand = os.path.join(os.path.dirname(os.path.abspath(target)), "shaping", "source-terms.json")
        if os.path.exists(cand):
            try:
                with open(cand, encoding="utf-8") as fh:
                    raw = json.load(fh)
                if isinstance(raw, dict):
                    raw = raw.get("terms") or raw.get("items") or []
                return [x if isinstance(x, str) else (x.get("name") or "") for x in raw if x]
            except Exception:
                return None
    return None


def _r_decision_ids(data):
    """`decisionId` 能指向的 id 集合。13 §1.3 只说「指向存在的决策」，不指定容器 ——
    本项目里可承载决策的有三处，取并集，避免为这一个字段新造顶层数组。"""
    ids = set()
    for k in ("decisions", "openQuestions", "annotations"):
        for x in (data.get(k) or []):
            if isinstance(x, dict) and x.get("id"):
                ids.add(x["id"])
    return ids


def _r_walk(node, out):
    if isinstance(node, dict):
        out.append(node)
        for ch in (node.get("children") or []):
            if isinstance(ch, dict):
                _r_walk(ch, out)
        for sl in (node.get("slots") or {}).values():
            for ch in (sl if isinstance(sl, list) else [sl]):
                _r_walk(ch, out)


def validate(data, rep: Report, strict=False):
    def gate(msg):
        """新语义检查的统一开关：交付档 ERROR、宽松档 WARN。

        为什么需要它：XX-021/019/020 这三条检查如果直接判 ERROR，存量 PRD
        会在升级当天全线判红，人的第一反应是关掉检查而不是补页面；如果一律 WARN，
        就会出现「errors=0 而页面层一片空白」——那正是 QMS 实测踩到的假绿。
        """
        (rep.error if strict else rep.warn)(msg)

    # 1. 顶层结构
    required = ["meta", "product", "users", "userFlows", "modules", "pages",
                "components", "stateMachines", "requirements", "boardPlan",
                "glossary", "openQuestions"]
    for k in required:
        if k not in data:
            rep.warn(f"缺少顶层字段 `{k}`（容器可降级渲染，但建议补齐）")
    # 交付档：AI 开发要照着排期与命令策略落地，缺了就只能自己编（XX-021）
    if strict:
        for k in ("tasks", "capabilities"):
            if not (data.get(k) or []):
                rep.error(f"[delivery] 缺少顶层 `{k}`（交付档必填："
                          f"tasks 说明谁先做什么、capabilities 说明谁在什么状态能点什么）")
    meta = data.get("meta") or {}
    if meta.get("schemaVersion") not in ("1.0", "1.1"):
        rep.warn(f"meta.schemaVersion 建议为 '1.0' 或 '1.1'，当前为 {meta.get('schemaVersion')!r}")
    if not data.get("pages"):
        rep.error("pages 为空：容器无内容可渲染")
        return

    # 2. ID 唯一性
    #    全局实体（user/module/page/flow/component/stateMachine/requirement/boardPlan/
    #    openQuestion）必须全局唯一；
    #    页内实体（node/interaction/state/annotation）只需在所属页面内唯一。
    all_ids = {}
    dup = []

    def reg(idv, kind):
        if not idv:
            return
        if idv in all_ids:
            dup.append(f"{idv}（{all_ids[idv]} 与 {kind} 重复）")
        else:
            all_ids[idv] = kind

    for u in data.get("users") or []:
        reg(u.get("id"), "user")
    for m in data.get("modules") or []:
        reg(m.get("id"), "module")
    for f in data.get("userFlows") or []:
        reg(f.get("id"), "userFlow")
    for c in data.get("components") or []:
        reg(c.get("id"), "component")
    for s in data.get("stateMachines") or []:
        reg(s.get("id"), "stateMachine")
    for r in data.get("requirements") or []:
        reg(r.get("id"), "requirement")
    for b in data.get("boardPlan") or []:
        reg(b.get("id"), "boardPlan")
    for q in data.get("openQuestions") or []:
        reg(q.get("id"), "openQuestion")
    for cp in data.get("capabilities") or []:
        reg(cp.get("id"), "capability")
    for tk in data.get("tasks") or []:
        reg(tk.get("id"), "task")
    for p in data.get("pages") or []:
        reg(p.get("id"), "page")
    if dup:
        rep.error("ID 重复：" + "；".join(dup[:10]))

    # 页内唯一
    for p in data.get("pages") or []:
        pid = p.get("id")
        local, ldup = {}, []

        def lreg(idv, kind):
            if not idv:
                return
            if idv in local:
                ldup.append(f"{idv}（{local[idv]} 与 {kind}）")
            else:
                local[idv] = kind

        for st in p.get("states") or []:
            lreg(st.get("id"), "state")
        for ix in p.get("interactions") or []:
            lreg(ix.get("id"), "interaction")
        for a in p.get("annotations") or []:
            lreg(a.get("id"), "annotation")
        nodes = []
        walk_nodes(p.get("componentTree") or {}, nodes)
        for n in nodes:
            lreg(n.get("id"), "node")
        if ldup:
            rep.error(f"[{pid}] 页内 ID 重复：" + "；".join(ldup[:8]))

    # 前缀规范
    for idv, kind in all_ids.items():
        ok = any(idv.startswith(p) for p in ID_PREFIXES)
        if not ok:
            rep.warn(f"ID `{idv}`（{kind}）未使用约定前缀：{list(ID_PREFIXES)[:6]}…")

    node_ids = collect_node_ids(data)
    page_ids = {p.get("id") for p in data.get("pages") or []}
    pages_by_id = {p.get("id"): p for p in data.get("pages") or []}
    module_ids = {m.get("id") for m in data.get("modules") or []}
    user_ids = {u.get("id") for u in data.get("users") or []}
    sm_ids = {s.get("id") for s in data.get("stateMachines") or []}
    req_ids = {r.get("id") for r in data.get("requirements") or []}
    flow_ids = {f.get("id") for f in data.get("userFlows") or []}

    # 3+4+5 逐页校验
    for p in data.get("pages") or []:
        pid = p.get("id")
        # 模块归属
        if p.get("moduleId") and p.get("moduleId") not in module_ids:
            rep.error(f"[{pid}] moduleId `{p.get('moduleId')}` 不存在")
        # 多级页面（parentId，用于左侧导航树）
        par_id = p.get("parentId")
        if par_id:
            if par_id == pid:
                rep.error(f"[{pid}] parentId 指向自身")
            elif par_id not in page_ids:
                rep.error(f"[{pid}] parentId `{par_id}` 不存在")
            else:
                # 环检测
                seen, cur, guard = {pid}, par_id, 0
                while cur and guard < 50:
                    if cur in seen:
                        rep.error(f"[{pid}] parentId 链存在环，经过 `{cur}`")
                        break
                    seen.add(cur)
                    guard += 1
                    parent = next((q for q in data.get("pages") or []
                                   if q.get("id") == cur), None)
                    cur = (parent or {}).get("parentId")
                # 跨模块挂载提示
                parent = next((q for q in data.get("pages") or []
                               if q.get("id") == par_id), None)
                if parent and p.get("moduleId") and parent.get("moduleId") \
                        and parent.get("moduleId") != p.get("moduleId"):
                    rep.warn(f"[{pid}] parentId `{par_id}` 属于其他模块 "
                             f"`{parent.get('moduleId')}`，导航树中会挂在父页面所在模块下")
        # 默认状态
        states = p.get("states") or []
        state_ids = {s.get("id") for s in states}
        if not states:
            rep.error(f"[{pid}] 缺少 states，容器无法模拟页面状态")
        if p.get("defaultStateId") and p.get("defaultStateId") not in state_ids:
            rep.error(f"[{pid}] defaultStateId `{p.get('defaultStateId')}` 不在 states 中")
        # 四态覆盖
        na_states = {str(x).lower() for x in (p.get("notApplicableStates") or [])}
        names = " ".join(
            f"{s.get('id','')} {s.get('name','')} {s.get('description','')}"
            for s in states).lower()
        for key, kws in STATE_KEYS.items():
            if key in na_states:
                rep.info(f"[{pid}] 「{key}」态已声明为不适用，跳过检查")
                continue
            if not any(k.lower() in names for k in kws):
                rep.warn(f"[{pid}] 未覆盖「{key}」态（默认/加载/空/异常四态建议齐全；"
                         f"若不适用请在页面加 notApplicableStates: [\"{key}\"]）")
        # 组件类型白名单 + 结构
        nodes = []
        walk_nodes(p.get("componentTree") or {}, nodes)
        if not nodes:
            rep.error(f"[{pid}] componentTree 为空或缺少 id/type")
        unknown = sorted({n.get("type") for n in nodes
                          if n.get("type") and n.get("type") not in WHITELIST})
        if unknown:
            rep.error(f"[{pid}] 使用了白名单外的组件类型：{unknown}")
        for n in nodes:
            if not n.get("type"):
                rep.error(f"[{pid}] 节点 `{n.get('id')}` 缺少 type")
            # 节点级未知字段：props 写错层是最常见的静默失效原因
            # （例：List 的 renderItem 写到节点级 → 容器读不到 → 列表渲染成空）
            extra = sorted(set(n) - NODE_KEYS)
            if extra:
                rep.warn(f"[{pid}] 节点 `{n.get('id')}` 含未识别的节点级字段 {extra}；"
                         f"组件属性请写在 `props` 内（允许的节点级字段：{sorted(NODE_KEYS)}）")
            if n.get("type") == "List":
                pr = n.get("props") or {}
                if "renderItem" not in pr and not isinstance(pr.get("itemTemplate"), dict) \
                        and pr.get("data") and not n.get("renderItem"):
                    rep.warn(f"[{pid}] List `{n.get('id')}` 有 data 但缺少 props.renderItem，"
                             f"容器会渲染成空列表")
        # 交互目标 / 覆写目标 / 标注锚点
        page_node_types = {n.get("id"): n.get("type") for n in nodes}
        # 筛选区按钮的合成节点 + 反向校验（见 filter_button_ids 的说明）。
        # 顺序很重要：先登记再校验交互，否则 ix-query 会先报「节点不存在」。
        for n in nodes:
            for iid in filter_button_ids(n):
                page_node_types[iid] = "Button"
            for key, iid in filter_ids_not_rendered(n):
                rep.error(f"[{pid}] Table `{n.get('id')}` 声明了 props.{key} = `{iid}`，"
                          f"但筛选区渲染器不会生成这个按钮 —— 只有 `filterBar:'grid3'` 且 "
                          f"`query` 非空时容器才渲染「重置 / 查询」并挂 id；"
                          f"否则这条 id 指向一个画不出来的按钮（只认 id 不验存在就是放宽）")
        # Table 的 props.rowClick / columns[].actions 决定合成 id 是否存在
        table_row_click = {}
        table_act_keys = {}
        table_row_keys = {}
        for n in nodes:
            if n.get("type") != "Table":
                continue
            pr = n.get("props") or {}
            table_row_click[n.get("id")] = bool(pr.get("rowClick"))
            keys = set()
            for c in pr.get("columns") or []:
                if isinstance(c, dict) and c.get("type") == "action":
                    acts = c.get("actions") or [{"key": "edit"}, {"key": "delete"}]
                    for a in acts:
                        if isinstance(a, dict) and a.get("key"):
                            keys.add(str(a["key"]))
            table_act_keys[n.get("id")] = keys
            rk = set()
            for row in pr.get("data") or []:
                if isinstance(row, dict):
                    rk.update(row.keys())
            table_row_keys[n.get("id")] = rk

        # ---------- 主子表结构（MasterDetail，见 04-container-schema.md §6.7） ----------
        for n in nodes:
            if n.get("type") != "MasterDetail":
                continue
            nid = n.get("id")
            pr = n.get("props") or {}
            kids = [c for c in (n.get("children") or []) if isinstance(c, dict)]
            if len(kids) != 2:
                rep.error(f"[{pid}] MasterDetail `{nid}` 需要正好 2 个子节点"
                          f"（children[0]=主表 Table，children[1]=子表 Table），当前 {len(kids)} 个")
                continue
            m, d = kids[0], kids[1]
            for role, k in (("主表", m), ("子表", d)):
                if k.get("type") != "Table":
                    rep.error(f"[{pid}] MasterDetail `{nid}` 的{role} `{k.get('id')}` "
                              f"类型是 `{k.get('type')}`，应为 Table")
            mp = m.get("props") or {}
            if mp.get("rowClick"):
                rep.error(f"[{pid}] MasterDetail `{nid}` 的主表 `{m.get('id')}` 设了 "
                          f"props.rowClick —— 主子表里「点行 = 选中行」，容器会强制关掉它；"
                          f"要跳页请改用 columns[].actions 里的按钮")
            bind = pr.get("bind")
            if not bind:
                rep.warn(f"[{pid}] MasterDetail `{nid}` 未声明 props.bind"
                         f"（主表行字段 → 子表行字段），容器会默认用 `id` 匹配")
            else:
                rk = table_row_keys.get(m.get("id"), set())
                if rk and bind not in rk:
                    rep.error(f"[{pid}] MasterDetail `{nid}` 的 bind `{bind}` 不在主表数据字段里"
                              f"（现有：{sorted(rk)[:12]}）")
                bt = pr.get("bindTo") or bind
                dk = table_row_keys.get(d.get("id"), set())
                if dk and bt not in dk:
                    rep.error(f"[{pid}] MasterDetail `{nid}` 的子表匹配字段 `{bt}` 不存在"
                              f"（子表现有：{sorted(dk)[:12]}）")

        # ---------- 容器选型：对话框 / 抽屉 / 新页面 ----------
        for n in nodes:
            t = n.get("type")
            if t not in ("Modal", "Drawer"):
                continue
            nid = n.get("id")
            sub = node_subtree(n)
            if t == "Modal":
                nested = [x for x in sub if x is not n and x.get("type") == "Modal"]
                if nested:
                    rep.error(f"[{pid}] 对话框 `{nid}` 里又嵌了对话框（{nested[0].get('id')}）"
                              f"—— 禁止 dialogception，第二层请改用 Drawer 或新页面"
                              f"（见 08-container-choice.md §6）")
                fields = [x for x in sub if x.get("type") in FIELD_TYPES]
                if len(fields) > MODAL_MAX_FIELDS:
                    rep.error(f"[{pid}] 对话框 `{nid}` 承载了 {len(fields)} 个表单字段"
                              f"（阈值 {MODAL_MAX_FIELDS}）—— 长表单禁用对话框，"
                              f"请改用 Drawer 或新页面（见 08-container-choice.md §5）")
                elif len(fields) > MODAL_DETAIL_HINT_FIELDS:
                    rep.warn(f"[{pid}] 对话框 `{nid}` 有 {len(fields)} 个字段 —— 若是「详情」视图，"
                             f"对话框展不开关联信息与操作区，主从详情首选 Drawer")
            if t == "Drawer":
                for x in sub:
                    if x.get("type") != "Tabs":
                        continue
                    ntab = len((x.get("props") or {}).get("items") or [])
                    if ntab >= 3:
                        rep.warn(f"[{pid}] 抽屉 `{nid}` 里有 {ntab} 个 tab"
                                 f"—— 抽屉里塞多 tab 工作台应升级为新页面"
                                 f"（见 08-container-choice.md §6）")
                    break

        # ---------- 主子表提示：同一父节点下平铺多张表 ----------
        def scan_siblings(nd):
            if not isinstance(nd, dict):
                return
            kids = [c for c in (nd.get("children") or []) if isinstance(c, dict)]
            tabs_ = [c for c in kids if c.get("type") == "Table"]
            if len(tabs_) >= 2 and nd.get("type") != "MasterDetail":
                rep.info(f"[{pid}] `{nd.get('id') or 'root'}` 下平铺了 {len(tabs_)} 张 Table"
                         f"（{', '.join(x.get('id', '?') for x in tabs_[:4])}）—— "
                         f"若存在主从关系（点上行看下行），建议用 MasterDetail 包起来，"
                         f"子表可展开收起（见 04-container-schema.md §6.7）")
            for c in kids:
                scan_siblings(c)
        scan_siblings(p.get("componentTree") or {})

        def check_target(where, tgt):
            bad = resolve_target(tgt, page_node_types)
            if bad:
                rep.error(f"[{pid}] {where}：{bad}")
                return
            m = SYNTH_RE.match(tgt or "")
            if not m:
                return
            base, kind = m.group(1), m.group(2)
            if kind.startswith("row_") and not table_row_click.get(base):
                rep.warn(f"[{pid}] {where} 引用了行节点 `{tgt}`，但 Table `{base}` 未设置 "
                         f"props.rowClick: true，容器不会给行加 id")
            if kind.startswith("act_"):
                key = kind.split("_", 2)[2]
                declared = table_act_keys.get(base, set())
                if key == "*":
                    if not declared:
                        rep.warn(f"[{pid}] {where} 用通配引用了 `{tgt}` 的操作按钮，"
                                 f"但 Table `{base}` 的 columns[].actions 未声明任何 key")
                elif key not in declared:
                    rep.warn(f"[{pid}] {where} 引用了操作按钮 `{tgt}`，但 Table `{base}` 的 "
                             f"columns[].actions 未声明 key `{key}`（已声明：{sorted(declared)}）")

        for ix in p.get("interactions") or []:
            on = ix.get("on") or {}
            tgt = on.get("target")
            if tgt:
                check_target(f"交互 `{ix.get('id')}` 的 on.target", tgt)
            if on.get("event") and on.get("event") not in EVENT_WHITELIST:
                rep.error(f"[{pid}] 交互 `{ix.get('id')}` 的 on.event `{on.get('event')}` 不在白名单 {sorted(EVENT_WHITELIST)}")
            if not (ix.get("actions") or []):
                rep.warn(f"[{pid}] 交互 `{ix.get('id')}` 没有 actions")
            for act in ix.get("actions") or []:
                atype = act.get("type")
                if atype not in ACTION_WHITELIST:
                    rep.error(f"[{pid}] 交互 `{ix.get('id')}` 使用了白名单外的 action `{atype}`；"
                              f"可用：{sorted(ACTION_WHITELIST)}")
                    continue
                if atype == "navigate":
                    tpid = act.get("pageId")
                    if tpid not in page_ids:
                        rep.error(f"[{pid}] 交互 `{ix.get('id')}` 跳转到不存在的页面 `{tpid}`")
                    # navigate 可带 stateId：必须是「目标页」的状态
                    if act.get("stateId"):
                        tpage = pages_by_id.get(tpid) or {}
                        tstates = {s.get("id") for s in (tpage.get("states") or [])}
                        if act["stateId"] not in tstates:
                            rep.error(f"[{pid}] 交互 `{ix.get('id')}` navigate.stateId `{act['stateId']}` "
                                      f"不是目标页 `{tpid}` 的状态")
                    if act.get("params") is not None and not isinstance(act["params"], dict):
                        rep.error(f"[{pid}] 交互 `{ix.get('id')}` navigate.params 必须是对象")
                    elif isinstance(act.get("params"), dict):
                        # {{row.field}} 只有在「点表格行 / 行内操作按钮」时才有 row 上下文
                        mt = SYNTH_RE.match(tgt or "")
                        is_row_ctx = bool(mt and (mt.group(2).startswith("row_") or mt.group(2).startswith("act_")))
                        for pk, pv in act["params"].items():
                            if not isinstance(pv, str):
                                continue
                            for fld in re.findall(r"\{\{\s*row\.([A-Za-z0-9_]+)", pv):
                                if not is_row_ctx:
                                    rep.warn(f"[{pid}] 交互 `{ix.get('id')}` 的 params.{pk} 用了 "
                                             f"`{{{{row.{fld}}}}}`，但 on.target `{tgt}` 不是表格行/行内按钮，"
                                             f"点击时没有 row 上下文")
                                elif mt:
                                    avail = table_row_keys.get(mt.group(1), set())
                                    if avail and fld not in avail:
                                        rep.warn(f"[{pid}] 交互 `{ix.get('id')}` 的 params.{pk} 引用了 "
                                                 f"row.{fld}，但 Table `{mt.group(1)}` 的数据里没有该字段"
                                                 f"（可用：{sorted(avail)}）")
                if atype == "gotoState" and act.get("stateId") not in state_ids:
                    rep.error(f"[{pid}] 交互 `{ix.get('id')}` 切到不存在的状态 `{act.get('stateId')}`")
                if atype == "setNode":
                    check_target(f"交互 `{ix.get('id')}` 的 setNode", act.get("target"))
                if atype == "scrollTo":
                    if not act.get("target"):
                        rep.warn(f"[{pid}] 交互 `{ix.get('id')}` 的 scrollTo 缺少 target")
                    else:
                        check_target(f"交互 `{ix.get('id')}` 的 scrollTo", act.get("target"))
                if atype in ("showModal", "showDrawer", "hideModal", "hideDrawer"):
                    if not (act.get("modalId") or act.get("drawerId") or act.get("target")):
                        rep.warn(f"[{pid}] 交互 `{ix.get('id')}` 的 `{atype}` 缺少 modalId/drawerId/target")
                if atype == "message" and not (act.get("text") or "").strip():
                    rep.warn(f"[{pid}] 交互 `{ix.get('id')}` 的 message 没有 text")
                if atype == "delay" and not isinstance(act.get("ms"), (int, float)):
                    rep.warn(f"[{pid}] 交互 `{ix.get('id')}` 的 delay 缺少 ms")
        for st in states:
            for ov in st.get("overrides") or []:
                if ov.get("target") not in node_ids:
                    rep.error(f"[{pid}] 状态 `{st.get('id')}` 覆写目标 `{ov.get('target')}` 不存在")
            for hid in (st.get("hidden") or []):
                if hid not in node_ids:
                    rep.warn(f"[{pid}] 状态 `{st.get('id')}` hidden 列表含未知节点 `{hid}`")
        # 标注
        for a in p.get("annotations") or []:
            anc = a.get("anchor") or {}
            if anc.get("nodeId"):
                bad = resolve_target(anc.get("nodeId"), page_node_types)
                if bad:
                    rep.error(f"[{pid}] 标注 `{a.get('id')}` 锚点：{bad}")
            if a.get("status") not in ANNO_STATUS:
                rep.error(f"[{pid}] 标注 `{a.get('id')}` status 非法：{a.get('status')!r}")
            if a.get("status") == "resolved" and not (a.get("replies") or []):
                rep.warn(f"[{pid}] 标注 `{a.get('id')}` 已标记处理但没有处理说明（replies 为空）")
            if not (a.get("text") or "").strip():
                rep.warn(f"[{pid}] 标注 `{a.get('id')}` 内容为空")
        # 页面关系
        for e in (p.get("entryFrom") or []) + (p.get("exitTo") or []):
            if e not in page_ids:
                rep.error(f"[{pid}] 页面关系引用了不存在的页面 `{e}`")
        # PRD
        # 类型错就只报这一条，不许抛异常 —— 一旦抛出，validate() 整个中止，
        # 后面十几条判据（含 R1–R4）一条都不跑，而外层只留一句"校验过程异常"：
        # 那是"一个字段写错 → 全部判据静默消失"，比报错难查得多。
        prd = p.get("prd")
        if prd is not None and not isinstance(prd, dict):
            rep.error(f"[{pid}] prd 应为对象（含 sections / reqIds），当前是 {type(prd).__name__}")
            prd = {}
        prd = prd or {}
        if not (prd.get("sections") or []):
            rep.warn(f"[{pid}] 缺少 prd.sections")
        for rid in (prd.get("reqIds") or []):
            if rid not in req_ids:
                rep.error(f"[{pid}] prd.reqIds 引用了不存在的需求 `{rid}`")
        # PRD 小节：type="flow" 的小节会渲染成内嵌 SVG 流程图，必须自带节点与边
        for sec in (prd.get("sections") or []):
            stype = sec.get("type")
            if stype in (None, "", "text"):
                continue
            if stype != "flow":
                rep.warn(f"[{pid}] prd.sections `{sec.get('id')}` 的 type `{stype}` 未知（只支持 flow）")
                continue
            sid = sec.get("id", "?")
            fnodes = sec.get("nodes") or []
            fedges = sec.get("edges") or []
            if not fnodes:
                rep.error(f"[{pid}] 流程图 `{sid}` 缺少 nodes")
                continue
            if len(fnodes) < 2:
                rep.warn(f"[{pid}] 流程图 `{sid}` 只有 1 个节点，无法表达流程")
            fids = set()
            for n in fnodes:
                nid = n.get("id")
                if not nid:
                    rep.error(f"[{pid}] 流程图 `{sid}` 有节点缺少 id")
                    continue
                if nid in fids:
                    rep.error(f"[{pid}] 流程图 `{sid}` 节点 id `{nid}` 重复")
                fids.add(nid)
                if not (n.get("label") or "").strip():
                    rep.warn(f"[{pid}] 流程图 `{sid}` 节点 `{nid}` 缺少 label")
                kind = n.get("kind")
                if kind and kind not in {"start", "end", "decision", "warn", "process"}:
                    rep.warn(f"[{pid}] 流程图 `{sid}` 节点 `{nid}` 的 kind `{kind}` 不在 "
                             f"start/end/decision/warn/process 内")
            for e in fedges:
                if e.get("from") not in fids:
                    rep.error(f"[{pid}] 流程图 `{sid}` 边 from `{e.get('from')}` 不存在")
                if e.get("to") not in fids:
                    rep.error(f"[{pid}] 流程图 `{sid}` 边 to `{e.get('to')}` 不存在")
                if e.get("from") and e.get("from") == e.get("to"):
                    rep.warn(f"[{pid}] 流程图 `{sid}` 存在自环边 `{e.get('from')}`")
            if fedges:
                touched = {e.get("from") for e in fedges} | {e.get("to") for e in fedges}
                for nid in sorted(fids - touched):
                    rep.warn(f"[{pid}] 流程图 `{sid}` 节点 `{nid}` 是孤岛（没有任何边相连）")
            if not (sec.get("caption") or "").strip():
                rep.warn(f"[{pid}] 流程图 `{sid}` 建议补 caption（图注），便于 AI 理解该图的用途")
        # 布局
        lay = p.get("layout")
        if lay and lay not in {"blank", "header-content", "sider-content", "header-sider-content"}:
            rep.warn(f"[{pid}] layout `{lay}` 不在约定枚举内")

    # 6. 需求 EARS 门禁
    for r in data.get("requirements") or []:
        rid = r.get("id", "?")
        pat = r.get("pattern")
        if pat not in EARS_PATTERNS:
            rep.error(f"[{rid}] pattern `{pat}` 不在 EARS 五种句式内")
        trig = (r.get("trigger") or "").strip()
        if pat and not eval_pattern_trigger_ok(pat, trig):
            rep.error(f"[{rid}] pattern={pat} 时 trigger 必须为空，当前为 {trig!r}")
        if pat in {"event-driven"} and not trig:
            rep.error(f"[{rid}] event-driven 句式必须填写 trigger")
        if r.get("moduleId") and r.get("moduleId") not in module_ids:
            rep.error(f"[{rid}] moduleId `{r.get('moduleId')}` 不存在")
        if r.get("pageId") and r.get("pageId") not in page_ids:
            rep.error(f"[{rid}] pageId `{r.get('pageId')}` 不存在")
        # XX-020：需求到交互的绑定，与 transitions[].ui 同构的三态声明：
        #   {"interactionId": "ix-xxx"}  由某个交互触发
        #   {"kind": "system"}           系统自动（回传 WMS、自动建单）
        #   {"kind": "page-enter"}       进页面即满足，不需要点击
        # 为什么不拿 `pattern` 当判据：`pattern` 的实际标错率很高（系统动作标成
        # event-driven、人点按钮标成 state-driven），拿它当前提，判据本身就不成立。
        # 一条 ui 声明的成本，换掉「忘了绑」与「本来不需要绑」分不清——后者正是
        # QMS 那 11 条「界面上有按钮但没声明」的成因。
        rui = r.get("ui")
        rpage = r.get("pageId")
        if rui is None:
            gate(f"[XX-020] 需求 {rid}（{r.get('title') or '未命名'}）缺少 ui："
                 f"三选一 {{\"interactionId\":\"ix-xxx\"}} / {{\"kind\":\"system\"}} / "
                 f"{{\"kind\":\"page-enter\"}}")
        elif not isinstance(rui, dict):
            rep.error(f"[XX-020] 需求 {rid} 的 ui 应为对象，当前为 {type(rui).__name__}（L3）")
        else:
            rkind, rix = rui.get("kind"), rui.get("interactionId")
            # 需求侧的页面归属只有一个真源：同级 `pageId`。`ui.pageId` 不会被任何
            # 检查读取 —— 它是数据契约里的假字段：写了不报错、也永远不生效，
            # 于是"ui 说 A 页、同级说 B 页"两档都会静默通过（实测：REQ-PO-001
            # 同级 page-po-create + ui.pageId=page-po-approve → rc=0 errors=0）。
            # 声明看起来完整、校验器却当它不存在，比漏检更坏，所以出现即 ERROR。
            # 三态都要拦：kind=system / page-enter 时同样不许带 pageId。
            if "pageId" in rui:
                # 报错里直接给出"这一条应该长什么样"：三态各自只保留自己的那个键，
                # 别让人读完报错还要回去翻文档。
                if rkind in ("system", "page-enter"):
                    hint = '{"kind": "%s"}' % rkind
                elif rix:
                    hint = '{"interactionId": "%s"}' % rix
                else:
                    hint = '{"interactionId": "ix-xxx"}'
                rep.error(f"[XX-020] 需求 {rid} 的 ui 里不应出现 pageId（L3）："
                          f"需求侧的页面归属取同级 pageId（当前 {rpage or '未声明'}），"
                          f"ui 只写 {hint}")
            if rkind is not None and rkind not in ("system", "page-enter"):
                rep.error(f"[XX-020] 需求 {rid} 的 ui.kind `{rkind}` 不合法："
                          f"只允许 `system` / `page-enter`（L3）")
            elif rkind in ("system", "page-enter"):
                pass                     # 系统动作 / 进页面即满足，不需要 interactionId
            elif not rix:
                rep.error(f"[XX-020] 需求 {rid} 的 ui 既没有 interactionId 也没有合法 kind（L3）")
            elif not rpage:
                rep.error(f"[XX-020] 需求 {rid} 的 ui.interactionId `{rix}` 缺少 pageId，无法定位（L2）")
            elif rpage in page_ids:
                avail = interaction_ids_of(pages_by_id.get(rpage))
                if rix not in avail:
                    rep.error(f"[XX-020] 需求 {rid} 的 ui.interactionId `{rix}` 不在页面 "
                              f"`{rpage}` 的 interactions 中（该页现有：{sorted(avail)}）（L2）")
        # XX-023：guards[] / effects[] —— 前置校验与后置影响有地方写。
        # 为什么需要它：规范要求「源文档每条必须/不得/否则都要落位」，但模型即使想到了
        # 前置校验也**写不进去**——没有承载结构。QMS 实测里「发起检验要先编质检标准」
        # 这类前置条件全靠散文，换个模型读就丢。
        # 严重度：缺字段不报（存量产物没有它，与 XX-020 的分层同理）；
        # 写了就必须写对——`kind` 只有 block/warn，写别的等于门不存在。
        gs = r.get("guards")
        if gs is not None:
            if not isinstance(gs, list):
                rep.error(f"[XX-023] 需求 {rid} 的 guards 应为数组，当前为 {type(gs).__name__}")
                gs = []
            for gi, g in enumerate(gs):
                if not isinstance(g, dict):
                    rep.error(f"[XX-023] 需求 {rid} 的 guards[{gi}] 应为对象 "
                              f'{{"text":"…","kind":"block|warn"}}')
                    continue
                if not str(g.get("text") or "").strip():
                    rep.error(f"[XX-023] 需求 {rid} 的 guards[{gi}] 缺少 text："
                              f"一条前置校验必须能一句话说清")
                if g.get("kind") not in ("block", "warn"):
                    rep.error(f"[XX-023] 需求 {rid} 的 guards[{gi}].kind `{g.get('kind')}` 不合法："
                              f"只能是 block（不满足就拦住）或 warn（提示但放行）")
        es = r.get("effects")
        if es is not None:
            if not isinstance(es, list):
                rep.error(f"[XX-023] 需求 {rid} 的 effects 应为数组，当前为 {type(es).__name__}")
                es = []
            for ei, e in enumerate(es):
                if not isinstance(e, dict):
                    rep.error(f"[XX-023] 需求 {rid} 的 effects[{ei}] 应为对象 "
                              f'{{"text":"…","target":"…"}}')
                    continue
                if not str(e.get("text") or "").strip():
                    rep.error(f"[XX-023] 需求 {rid} 的 effects[{ei}] 缺少 text："
                              f"推进后系统自动做了什么必须写出来")
        if r.get("role") and r.get("role") not in user_ids and r.get("role") != "system":
            rep.warn(f"[{rid}] role `{r.get('role')}` 不在 users 中（系统行为请写 'system'）")
        if r.get("stateMachine") and r.get("stateMachine") not in sm_ids:
            rep.error(f"[{rid}] stateMachine `{r.get('stateMachine')}` 不存在")
        if r.get("status") not in REQ_STATUS:
            rep.warn(f"[{rid}] status `{r.get('status')}` 非法（应为 draft/confirmed）")
        if r.get("source") not in REQ_SOURCE:
            rep.warn(f"[{rid}] source `{r.get('source')}` 非法（应为 user/demo/inferred）")
        # 可验证性
        blob = " ".join(str(r.get(k, "")) for k in ("expected", "rule", "title"))
        hit = [w for w in SUBJECTIVE_WORDS if w in blob]
        if hit:
            rep.error(f"[{rid}] 含主观词 {hit}，不可验证，需改为量化描述")
        impl = [w for w in IMPL_HINTS if w in blob]
        if impl:
            rep.warn(f"[{rid}] 疑似含实现细节 {impl}，需求应描述行为而非实现")
        acc = r.get("acceptance") or []
        if len(acc) < 2:
            rep.error(f"[{rid}] acceptance 少于 2 条（需含正常路径与边界/异常）")
        if r.get("stateMachine") and pat in {"event-driven", "unwanted"}:
            joined = " ".join(acc)
            if not any(k in joined for k in ("拒绝", "不可", "禁用", "非法",
                                             "不允许", "置灰", "终态", "回退")):
                rep.warn(f"[{rid}] 关联状态机但验收条件未覆盖「非法流转被拒绝」")
        # 单一响应启发式
        exp = str(r.get("expected", ""))
        if exp.count("并且") + exp.count("以及") >= 2:
            rep.warn(f"[{rid}] expected 可能包含多个响应，建议拆分为多条需求")
        # inferred 需有对应 openQuestion
        if r.get("source") == "inferred":
            oq = " ".join((q.get("question", "") + q.get("answer", ""))
                          for q in data.get("openQuestions") or [])
            if r.get("title", "") not in oq and rid not in oq:
                rep.warn(f"[{rid}] source=inferred 但 openQuestions 中未见对应确认项")

    # 7. 状态机
    for sm in data.get("stateMachines") or []:
        sid = sm.get("id", "?")
        sids = {s.get("id") for s in sm.get("states") or []}
        if not sids:
            rep.error(f"[{sid}] states 为空")
            continue
        if sm.get("initial") not in sids:
            rep.error(f"[{sid}] initial `{sm.get('initial')}` 不在 states 中")
        has_in, has_out = set(), set()
        for t in sm.get("transitions") or []:
            if t.get("from") not in sids:
                rep.error(f"[{sid}] 转移 `{t.get('id')}` 的 from `{t.get('from')}` 不存在")
            if t.get("to") not in sids:
                rep.error(f"[{sid}] 转移 `{t.get('id')}` 的 to `{t.get('to')}` 不存在")
            if not (t.get("trigger") or "").strip():
                rep.warn(f"[{sid}] 转移 `{t.get('id')}` 缺少 trigger")
            if t.get("role") and t.get("role") not in user_ids and t.get("role") != "system":
                rep.warn(f"[{sid}] 转移 `{t.get('id')}` 的 role `{t.get('role')}` 不在 users 中")
            # XX-019：人工转移必须写明「由哪个页面的哪个交互触发」。
            # 没有它，状态机就只能证明「流程想清楚了」，证明不了「页面能点出来」——
            # QMS 实测：17 条非 system 转移一条都没写，审核通过 / 审核驳回在页面上根本无按钮。
            # 文本固定以 `转移 <id>` 开头：验收要靠 grep -oE "转移 (nt|it|st|nr)-[0-9]+"
            # 抓 id 集合，格式一变断言就静默变空 —— 行首写死，别让下游去猜。
            ui = t.get("ui")
            tid = t.get("id")
            label = f"转移 {tid}（{sid}，{t.get('from')}→{t.get('to')}，" \
                    f"{t.get('trigger') or '未命名'}）"
            if transition_is_system(t):
                pass                     # 系统自动触发，没有按钮可点，不参与校验
            elif ui is None:
                gate(f"[XX-019] {label} 缺少 ui：这条转移由哪个页面的哪个交互触发？"
                     f"人工转移请写 ui:{{pageId, interactionId}}，"
                     f"系统自动流转请写 ui:{{\"kind\":\"system\"}}")
            elif not isinstance(ui, dict):
                gate(f"[XX-019] {label} 的 ui 应为对象 {{pageId, interactionId}}，"
                     f"当前为 {type(ui).__name__}")
            elif ui.get("kind") != "system":
                upid, uix = ui.get("pageId"), ui.get("interactionId")
                if not upid:
                    gate(f"[XX-019] {label} 的 ui 缺少 pageId")
                elif upid not in page_ids:
                    rep.error(f"[XX-019] {label} 的 ui.pageId `{upid}` 不存在")
                elif not uix:
                    gate(f"[XX-019] {label} 的 ui 缺少 interactionId（页面 `{upid}`）")
                else:
                    avail = interaction_ids_of(pages_by_id.get(upid))
                    if uix not in avail:
                        # 悬空引用是「写错了」，不是「没写」——两档都 ERROR，
                        # 与 XX-020 的 L2（:815）以及本块的 ui.pageId 不存在（:894）同一严重度。
                        # L1 类（缺 pageId / 缺 interactionId / ui 不是对象）仍走 gate()，
                        # 让未声明 ui 的存量产物在默认档活着。
                        rep.error(f"[XX-019] {label} 指向的交互 `{uix}` 不在页面 `{upid}` 的 "
                                  f"interactions 中（该页现有：{sorted(avail)}）")
            has_in.add(t.get("to"))
            has_out.add(t.get("from"))
        for st in sids:
            if st == sm.get("initial"):
                if st not in has_out and len(sids) > 1:
                    rep.warn(f"[{sid}] 初始状态 `{st}` 没有任何出边")
                continue
            if st not in has_in and st not in has_out:
                rep.warn(f"[{sid}] 孤立状态 `{st}`：既无入边也无出边")

    # 8. boardPlan
    for b in data.get("boardPlan") or []:
        if b.get("status") not in BOARD_STATUS:
            rep.error(f"[bp] `{b.get('id')}` status `{b.get('status')}` 非法（todo/doing/done）")
        if b.get("pageId") and b.get("pageId") not in page_ids:
            rep.error(f"[bp] `{b.get('id')}` pageId `{b.get('pageId')}` 不存在")
        for rid in b.get("reqIds") or []:
            if rid not in req_ids:
                rep.error(f"[bp] `{b.get('id')}` reqIds 引用不存在的需求 `{rid}`")

    # 9. userFlows / 模块
    for f in data.get("userFlows") or []:
        if f.get("role") and f.get("role") not in user_ids:
            rep.warn(f"[flow] `{f.get('id')}` role `{f.get('role')}` 不在 users 中")
        for s in f.get("steps") or []:
            if s.get("pageId") and s.get("pageId") not in page_ids:
                rep.error(f"[flow] `{f.get('id')}` 步骤 `{s.get('id')}` pageId `{s.get('pageId')}` 不存在")
    for m in data.get("modules") or []:
        for pid2 in m.get("pageIds") or []:
            if pid2 not in page_ids:
                rep.error(f"[module] `{m.get('id')}` pageIds 含不存在的页面 `{pid2}`")

    # 10. dataModel（机器可读的数据实体，供 AI 生成 TS 类型 / mock / 接口契约）
    dm = data.get("dataModel")
    if dm is None:
        rep.info("未提供 dataModel：devspec 仍可导出，但后端建模需自行补全")
    else:
        if isinstance(dm, list):
            ents = dm
            derived = []
            rep.warn("dataModel 建议写成 {entities:[...], derived:[...]} 对象形式")
        else:
            ents = dm.get("entities") or []
            derived = dm.get("derived") or []
        if not ents:
            rep.warn("dataModel.entities 为空")
        ent_ids, ent_names = set(), set()
        for en in ents:
            eid = en.get("id")
            if not eid:
                rep.error("[dataModel] 存在缺少 id 的实体")
                continue
            if eid in ent_ids:
                rep.error(f"[dataModel] 实体 id `{eid}` 重复")
            ent_ids.add(eid)
            nm = en.get("name")
            if not nm:
                rep.error(f"[dataModel] 实体 `{eid}` 缺少 name（建议用大驼峰实体名）")
            elif nm in ent_names:
                rep.warn(f"[dataModel] 实体 name `{nm}` 重复")
            else:
                ent_names.add(nm)
            if not en.get("table"):
                rep.warn(f"[dataModel] 实体 `{eid}` 缺少 table（物理表名），AI 生成接口契约时会自行猜测")
            flds = en.get("fields") or []
            if not flds:
                rep.error(f"[dataModel] 实体 `{eid}` 缺少 fields")
            fnames = set()
            pk = 0
            for f in flds:
                fn = f.get("name")
                if not fn:
                    rep.error(f"[dataModel] 实体 `{eid}` 有字段缺少 name")
                    continue
                if fn in fnames:
                    rep.error(f"[dataModel] 实体 `{eid}` 字段 `{fn}` 重复")
                fnames.add(fn)
                if not f.get("type"):
                    rep.warn(f"[dataModel] `{eid}.{fn}` 缺少 type")
                if f.get("key") == "pk":
                    pk += 1
            if pk == 0:
                rep.warn(f"[dataModel] 实体 `{eid}` 没有标 key:\"pk\" 的主键字段")
            elif pk > 1:
                rep.error(f"[dataModel] 实体 `{eid}` 标了 {pk} 个主键")
            for pid3 in en.get("pageIds") or []:
                if pid3 not in page_ids:
                    rep.error(f"[dataModel] 实体 `{eid}` pageIds 含不存在的页面 `{pid3}`")
        # 关系目标必须存在
        for en in ents:
            for rel in en.get("relations") or []:
                tgt = rel.get("target")
                if tgt not in ent_ids:
                    rep.error(f"[dataModel] 实体 `{en.get('id')}` 的关系 target `{tgt}` 不存在")
                if not rel.get("type"):
                    rep.warn(f"[dataModel] 实体 `{en.get('id')}` 的关系缺少 type（belongs_to/has_many/…）")
        for d in derived:
            if not d.get("name"):
                rep.error("[dataModel.derived] 存在缺少 name 的派生字段")
                continue
            if not (d.get("expr") or "").strip():
                rep.warn(f"[dataModel.derived] `{d.get('name')}` 缺少 expr")
            if not (d.get("fallback") or "").strip():
                rep.warn(f"[dataModel.derived] `{d.get('name')}` 建议写 fallback（除零 / 空值时的展示）")
            for pid4 in d.get("usedBy") or []:
                if pid4 not in page_ids:
                    rep.error(f"[dataModel.derived] `{d.get('name')}` usedBy 含不存在的页面 `{pid4}`")
            if d.get("reqId") and d["reqId"] not in req_ids:
                rep.error(f"[dataModel.derived] `{d.get('name')}` reqId `{d['reqId']}` 不存在")
        if ents:
            rep.info(f"dataModel：{len(ents)} 个实体 / {sum(len(e.get('fields') or []) for e in ents)} 个字段"
                     f" / {len(derived)} 个派生字段")

    # 10.5 行为建模：capabilities（角色 × 状态 × 命令）+ 页面职责契约
    #      这一步检查的是「语义」而非「结构」：按钮与状态、命令与页面之间是否连得上。
    sm_by_entity = {}
    for s in data.get("stateMachines") or []:
        if s.get("entity"):
            sm_by_entity.setdefault(s["entity"], s)
    ents_for_cap = set()
    dm2 = data.get("dataModel")
    if isinstance(dm2, dict):
        for en in dm2.get("entities") or []:
            ents_for_cap.add(en.get("id"))
            if en.get("name"):
                ents_for_cap.add(en["name"])

    caps = data.get("capabilities") or []
    cap_by_id = {}
    for cp in caps:
        cid = cp.get("id") or "<无 id>"
        if cp.get("id"):
            cap_by_id[cid] = cp
        miss = [k for k in ("id", "name", "entity", "actor", "policy") if cp.get(k) in (None, "", [])]
        if "from" not in cp:
            miss.append("from")          # 允许 `from: []`（表示不限状态），但字段必须显式写出来
        if miss:
            rep.error(f"[cap] `{cid}` 缺少必填字段：{'、'.join(miss)}")
        if cp.get("id") and not str(cp["id"]).startswith("cap-"):
            rep.warn(f"[cap] `{cid}` 建议以 `cap-` 开头")
        ent = cp.get("entity")
        if ent and ents_for_cap and ent not in ents_for_cap:
            rep.error(f"[cap] `{cid}` entity `{ent}` 不在 dataModel.entities 中")
        for a in cp.get("actor") or []:
            if a not in user_ids:
                rep.error(f"[cap] `{cid}` actor `{a}` 不在 users 中")
        pol = cp.get("policy")
        if pol and pol not in CAP_POLICIES:
            rep.error(f"[cap] `{cid}` policy `{pol}` 非法（hidden / disabled / reject）")
        if pol in ("hidden", "disabled") and (cp.get("from") or []):
            # from 为空 = 不限状态，policy 永远不会触发，也就不需要 reason
            reason = (cp.get("reason") or "").strip()
            if not reason:
                rep.error(f"[cap] `{cid}` policy=`{pol}` 必须写 reason（用户要知道为什么不能点）")
            elif reason in CAP_VAGUE_REASONS:
                rep.warn(f"[cap] `{cid}` reason「{reason}」太笼统，应说明当前状态 + 允许状态")
        sm = sm_by_entity.get(ent) if ent else None
        state_ids = {x.get("id") for x in (sm or {}).get("states") or []}
        for st in cp.get("from") or []:
            if state_ids and st not in state_ids:
                rep.error(f"[cap] `{cid}` from 中的状态 `{st}` 不在状态机 `{sm.get('id')}` 里")
        to = cp.get("to")
        if to:
            if state_ids and to not in state_ids:
                rep.error(f"[cap] `{cid}` to `{to}` 不在状态机 `{sm.get('id')}` 里")
            elif sm:
                ok_tr = any(t.get("from") in (cp.get("from") or []) and t.get("to") == to
                            for t in sm.get("transitions") or [])
                if not ok_tr:
                    rep.error(f"[cap] `{cid}` 声称状态 {cp.get('from')} → `{to}`，"
                              f"但状态机 `{sm.get('id')}` 没有对应转移")
        if cp.get("page") and cp["page"] not in page_ids:
            rep.error(f"[cap] `{cid}` page `{cp['page']}` 不存在")
        if cp.get("requirement") and cp["requirement"] not in req_ids:
            rep.error(f"[cap] `{cid}` requirement `{cp['requirement']}` 不存在")

    # 状态机的每条人工转移，都应有对应命令；标了 system:true 的自动转移除外
    caps_by_entity = {}
    for cp in caps:
        caps_by_entity.setdefault(cp.get("entity"), []).append(cp)
    for sm in data.get("stateMachines") or []:
        ent = sm.get("entity")
        mine = caps_by_entity.get(ent) or []
        if not mine:
            rep.warn(f"[sm] 状态机 `{sm.get('id')}`（{ent}）没有任何命令策略（capabilities）："
                     f"各状态下按钮该可用还是置灰无从判断")
            continue
        for t in sm.get("transitions") or []:
            if t.get("system"):
                continue
            hit = any(t.get("from") in (c.get("from") or []) and c.get("to") == t.get("to") for c in mine)
            if not hit:
                rep.error(f"[sm] `{sm.get('id')}` 的转移 {t.get('from')}→{t.get('to')}"
                          f"（{t.get('trigger') or '未命名'}）没有对应 capability，"
                          f"用户无法从界面上触发它；若为系统自动流转请标 `system:true`")

    # 页面职责契约
    owns_owner = {}
    for p in data.get("pages") or []:
        pid = p.get("id")
        ctr = p.get("contract")
        if ctr is None:
            if strict:
                # 交付档不再依赖 page.entity：旧写法把提示挂在 `p.entity` 上，
                # 于是「页面根本不写 entity」的 PRD 这条检查完全静默 —— 11 个页面
                # 一条 contract 都没有，校验器却报 PASS。这正是 XX-021 要堵的洞。
                rep.error(f"[delivery] [page] `{pid}` 缺少 contract（交付档必填："
                          f"这个页面负责哪条任务、哪些命令、提交边界是什么）")
            else:
                sm = sm_by_entity.get(p.get("entity")) if p.get("entity") else None
                if sm:
                    rep.warn(f"[page] `{pid}` 绑定了实体 `{p.get('entity')}` 却没有 contract："
                             f"这个页面负责哪条任务、哪些命令说不清（见 references/10-page-decomposition.md）")
            continue
        if not isinstance(ctr, dict):
            rep.error(f"[page] `{pid}` contract 应为对象")
            continue
        miss = [k for k in CONTRACT_REQUIRED if ctr.get(k) in (None, "", [])]
        if miss:
            rep.error(f"[page] `{pid}` contract 缺少：{'、'.join(miss)}")
        if ctr.get("entity") and p.get("entity") and ctr["entity"] != p["entity"]:
            rep.error(f"[page] `{pid}` contract.entity `{ctr['entity']}` 与 page.entity `{p['entity']}` 不一致")
        for a in ctr.get("actor") or []:
            if a not in user_ids:
                rep.error(f"[page] `{pid}` contract.actor `{a}` 不在 users 中")
        for cid in ctr.get("owns") or []:
            if cid not in cap_by_id:
                rep.error(f"[page] `{pid}` contract.owns 引用不存在的 capability `{cid}`")
                continue
            if cid in owns_owner and owns_owner[cid] != pid:
                rep.error(f"[page] capability `{cid}` 被 `{owns_owner[cid]}` 与 `{pid}` 同时声明为"
                          f"主页面：同一命令只能有一个主页面")
            else:
                owns_owner[cid] = pid
            cp = cap_by_id[cid]
            if cp.get("page") and cp["page"] != pid:
                rep.error(f"[page] `{pid}` owns 了 `{cid}`，但该 capability 的 page 是 `{cp['page']}`")
        sb = ctr.get("submitBoundary")
        if sb and sb not in ("single", "staged", "none"):
            rep.error(f"[page] `{pid}` contract.submitBoundary `{sb}` 非法（single / staged / none）")

    # 命令有没有真的落到组件上（模型写了但没用 → 提示，不算错）
    for cp in caps:
        cid = cp.get("id")
        if not cid:
            continue
        bound = False
        for p in data.get("pages") or []:
            nodes = []
            walk_nodes(p.get("componentTree") or {}, nodes)
            for n in nodes:
                pr = n.get("props") or {}
                if pr.get("capability") == cid:
                    bound = True
                    break
                for col in pr.get("columns") or []:
                    for a in (col or {}).get("actions") or []:
                        if (a or {}).get("capability") == cid:
                            bound = True
                            break
            if bound:
                break
        if not bound:
            rep.info(f"[cap] `{cid}` 没有绑定到任何按钮（模型已建，但原型上看不到它的效果）")

    # 非法路径的验收覆盖：只写成功路径 = 只写了一半
    if caps:
        denial_ok = False
        for r in data.get("requirements") or []:
            if r.get("pattern") == "unwanted":
                denial_ok = True
                break
            for acc in r.get("acceptance") or []:
                if any(w in str(acc) for w in DENIAL_WORDS):
                    denial_ok = True
                    break
            if denial_ok:
                break
        if not denial_ok:
            rep.warn("已有命令策略，但没有任何需求覆盖「非法动作被拒绝 / 无权限 / 状态不符」的验收条件")

    # 多功能混页的启发式提示：一页多个表单 / 表单 + 多张表 / 多个主操作，且没有页面职责契约
    for p in data.get("pages") or []:
        if p.get("contract"):
            continue
        nodes = []
        walk_nodes_skip(p.get("componentTree") or {}, nodes, ("MasterDetail",))
        forms = [n for n in nodes if n.get("type") == "Form"]
        tables = [n for n in nodes if n.get("type") == "Table"]
        prim = 0
        for n in nodes:
            if n.get("type") == "Button":
                pr = n.get("props") or {}
                if pr.get("type") in ("primary", "danger") and not pr.get("capability"):
                    prim += 1
        if len(forms) >= 2 or (forms and len(tables) >= 2) or prim >= 3:
            rep.warn(f"[page] `{p.get('id')}` 疑似多功能混页（表单 {len(forms)} 个 / 表格 {len(tables)} 张 / "
                     f"主操作 {prim} 个）：确认它们是否同一角色、同一对象、同一提交边界，"
                     f"并补 `contract` 说明（见 references/10-page-decomposition.md）")

    if caps:
        rep.info(f"capabilities：{len(caps)} 条命令 / {len(owns_owner)} 条已声明主页面")

    # 11. 机器可读性总检：AI 开发所需的最小信息是否齐备
    missing = []
    if not (data.get("pages") or []):
        missing.append("pages")
    if not (data.get("requirements") or []):
        missing.append("requirements(EARS)")
    if not (data.get("modules") or []):
        missing.append("modules")
    if dm is None:
        missing.append("dataModel")
    if missing:
        rep.warn(f"机器可读性：缺少 {missing}，AI 据此开发会自行补全（建议补齐）")

    # 统计
    roots = [p for p in (data.get("pages") or []) if not p.get("parentId")]
    nested = len(data.get("pages") or []) - len(roots)
    rep.info(f"导航树：{len(data.get('modules') or [])} 个模块 / "
             f"{len(roots)} 个顶级页面 / {nested} 个子页面")
    rep.info(f"pages={len(data.get('pages') or [])} "
             f"modules={len(data.get('modules') or [])} "
             f"requirements={len(data.get('requirements') or [])} "
             f"stateMachines={len(data.get('stateMachines') or [])} "
             f"nodes={len(node_ids)}")
    # XX-023：guards / effects 的条数单独打一行。这不是装饰——"字段存在"和"里面有几条"
    # 是两件事，只报前者的话，一个 `guards: []` 和 7 条像话的守卫在输出上完全一样。
    reqs = data.get("requirements") or []
    n_guards = sum(len(r.get("guards") or []) for r in reqs if isinstance(r.get("guards"), list))
    n_effects = sum(len(r.get("effects") or []) for r in reqs if isinstance(r.get("effects"), list))
    n_g_req = sum(1 for r in reqs if isinstance(r.get("guards"), list) and r["guards"])
    n_e_req = sum(1 for r in reqs if isinstance(r.get("effects"), list) and r["effects"])
    rep.info(f"行为补充：guards={n_guards}（{n_g_req}/{len(reqs)} 条需求） "
             f"effects={n_effects}（{n_e_req}/{len(reqs)} 条需求）")

    # ============ 12. 需求准确性 R1–R4（references/13-requirements-accuracy.md）============
    # 三态必须分开：PASS / ERROR / INCOMPLETE。
    # INCOMPLETE = 「判据在，但产物里没有可判的输入」—— 既不许压成 PASS（会得到全绿的假象），
    # 也不许压成 ERROR（会把「没写输入」和「写错了」混成一件事，处置完全不同）。
    # 与 check_ui_shape 的 INCOMPLETE 同义，见 13 §5 的落地状态行。
    _rst = []

    def rchk(rid, ok, msg, inc=None, warn_only=False):
        if inc is not None:
            _rst.append((rid, "INCOMPLETE"))
            rep.incomplete(f"[{rid}] {inc}")
        elif ok:
            _rst.append((rid, "PASS"))
        elif warn_only and not strict:
            _rst.append((rid, "WARN"))
            rep.warn(f"[{rid}] {msg}")
        else:
            _rst.append((rid, "ERROR"))
            rep.error(f"[{rid}] {msg}")

    _pages = data.get("pages") or []
    _pages_by_id = {p.get("id"): p for p in _pages}
    _caps = data.get("capabilities") or []
    _tasks = data.get("tasks") or []
    _fr = data.get("fieldRegistry") or []
    _terms = _r_source_terms(data, rep.target)
    _dm = data.get("dataModel") or {}
    _rels = _dm.get("relations") or []
    _ones = [r for r in _rels if isinstance(r, dict) and r.get("kind") == "1:N"]
    _sms = data.get("stateMachines") or []
    _root_ids = {p.get("id") for p in _pages if not (p.get("entryFrom") or [])}

    # ---------------- R1 字段登记 ----------------
    if not _fr:
        for rid in ("R1-a", "R1-b", "R1-c", "R1-d"):
            rchk(rid, False, "", "缺顶层 `fieldRegistry[]`：登记表不存在，本条无从判（不是通过）")
    else:
        _idx = {pid: _r_page_index(p) for pid, p in _pages_by_id.items()}
        _dangling, _invisible = [], []
        for f in _fr:
            pid, bid = f.get("pageId"), f.get("block")
            if pid not in _idx:
                _dangling.append(f"{f.get('id')} 的 pageId `{pid}` 不存在")
                continue
            ids, texts = _idx[pid]
            if bid not in ids:
                _dangling.append(f"{f.get('id')} 的 block `{bid}` 在 `{pid}` 里不存在")
                continue
            core = _r_core(f.get("name"))
            if core and core not in (texts.get(bid) or ""):
                _invisible.append(
                    f"{f.get('id')}「{f.get('name')}」在 block `{bid}` 的可渲染文本里看不到「{core}」")
        rchk("R1-a", not _dangling, "悬空落位：" + "；".join(_dangling[:5]))
        rchk("R1-b", not _invisible, "落位不可见：" + "；".join(_invisible[:5]))

        if _terms is None:
            rchk("R1-c", False, "",
                 "无源点名词清单（顶层 `sourceTerms[]` 与 `<产物目录>/shaping/source-terms.json` 都不存在）："
                 "分母为 0 时「登记数 ≥ 0」恒成立，不能判")
        else:
            def _registered(t):
                c = _r_core(t)
                if not c:
                    return False
                for f in _fr:
                    fc = _r_core(f.get("name"))
                    if fc and (c in fc or fc in c):
                        return True
                return False

            _miss = [t for t in _terms if not _registered(t)]
            rchk("R1-c", not _miss,
                 f"源点名 {len(_terms)} 项、登记 {len(_fr)} 项，缺：{' / '.join(_miss[:6])}")

        _dec_ids = _r_decision_ids(data)
        _bad_d = [f"{f.get('id')} 缺 scope（只许 in/out）"
                  for f in _fr if f.get("scope") not in ("in", "out")]
        for f in _fr:
            if f.get("scope") == "out":
                if not (f.get("reason") or "").strip():
                    _bad_d.append(f"{f.get('id')} scope=out 但没有 reason")
                elif f.get("decisionId") not in _dec_ids:
                    _bad_d.append(f"{f.get('id')} 的 decisionId `{f.get('decisionId')}` 指向不存在的决策")
        rchk("R1-d", not _bad_d, "反向覆盖：" + "；".join(_bad_d[:5]))

    # ---------------- R2 一对多结构 ----------------
    _decided = [f for f in _fr if isinstance(f.get("oneToMany"), bool)]
    _o2m_true = [f for f in _fr if f.get("oneToMany") is True]
    if _terms is None:
        rchk("R2", False, "", "无源点名词清单：触发词命中数算不出，计数闭合判不了")
    else:
        _hits = [t for t in _terms if any(w in t for w in R2_TRIGGERS)]
        rchk("R2", len(_hits) == len(_decided),
             f"触发词命中 {len(_hits)} 条（{' / '.join(_hits[:4])}），"
             f"oneToMany 裁决 {len(_decided)} 条，两者应相等")

    if not _rels:
        rchk("R2-a", False, "",
             "`dataModel.relations` 为空：没有 1:N 声明可判（R4 的适用范围也因此为空）")
    else:
        rchk("R2-a", len(_ones) >= len(_o2m_true),
             f"oneToMany:true 的登记 {len(_o2m_true)} 条，relations 里只有 {len(_ones)} 条 kind='1:N'")

    if not _ones:
        rchk("R2-b", False, "", "没有 1:N 关系：子实体状态机无从判")
        rchk("R2-c", False, "", "没有 1:N 关系：子实体独立操作人无从判")
    else:
        _bad_b, _bad_c = [], []
        for r in _ones:
            child, parent = r.get("to"), r.get("from")
            _csm = [s for s in _sms if s.get("entity") == child]
            if not _csm:
                _bad_b.append(f"{parent}→{child} 缺子实体状态机")
            else:
                _cset = {st.get("id") or st.get("name") for st in (_csm[0].get("states") or [])}
                if len(_cset) < 3:
                    _bad_b.append(f"{child} 状态数 {len(_cset)} < 3")
                _psm = [s for s in _sms if s.get("entity") == parent]
                if _psm:
                    _pset = {st.get("id") or st.get("name") for st in (_psm[0].get("states") or [])}
                    if _cset and _cset <= _pset:
                        _bad_b.append(f"{child} 的状态集合 ⊆ {parent} 的（是投影，不是独立状态机）")
            _c_caps = [c for c in _caps if c.get("entity") == child]
            if not _c_caps:
                _bad_c.append(f"{child} 没有任何 capability（被当成主实体的一个字段了）")
            else:
                _ca, _pa = set(), set()
                for c in _c_caps:
                    _ca |= set(c.get("actor") or [])
                for c in _caps:
                    if c.get("entity") == parent:
                        _pa |= set(c.get("actor") or [])
                if _pa and _ca and _ca <= _pa and len(_ca) == len(_pa):
                    _bad_c.append(f"{child} 的操作人集合与 {parent} 完全相同（分不出两个环节）")
        rchk("R2-b", not _bad_b, "子实体状态机：" + "；".join(_bad_b[:4]))
        rchk("R2-c", not _bad_c, "子实体独立操作人：" + "；".join(_bad_c[:4]))

    # R2-d：子表里不许有「阶段 / 类型 / stage」列 —— 它说明两类单据被合并了。
    # 没有 MasterDetail 结构时判 PASS（不存在这个错误），不是 SKIP：这条判的是"有没有错误"，
    # 不是"有没有对象"。
    _bad_d2, _md_seen = [], 0
    for p in _pages:
        nodes = []
        tree = p.get("componentTree")
        for n in (tree if isinstance(tree, list) else [tree]):
            _r_walk(n, nodes)
        for n in nodes:
            if n.get("type") != "MasterDetail":
                continue
            _md_seen += 1
            # 子表 = `children[1]`（children[0] 是主表）。列在节点的 props.columns 里，
            # 不在 props.children 里 —— 后者是 I-07 之前的老写法，现有校验器要求节点级 children。
            for ch in (n.get("children") or [])[1:]:
                if not isinstance(ch, dict):
                    continue
                for col in ((ch.get("props") or {}).get("columns") or []):
                    t = (col.get("title") or "")
                    di = (col.get("dataIndex") or "")
                    if t in ("阶段", "类型") or "stage" in di:
                        _bad_d2.append(f"{p.get('id')} 的子表出现列「{t or di}」")
    rchk("R2-d", not _bad_d2, "合并结构：" + "；".join(_bad_d2[:4]))

    # ---------------- R3 角色待办归属（含 R3-b 独立待办页） ----------------
    _roles = []
    for c in _caps:
        for a in (c.get("actor") or []):
            if a not in _roles:
                _roles.append(a)
    if not _roles:
        rchk("R3", False, "", "`capabilities[].actor` 为空：没有角色可判")
        rchk("R3-b", False, "", "同上：无角色、也无 stage，独立待办页无从判")
    elif not any(isinstance(p.get("contract"), dict) and p.get("contract") for p in _pages):
        # 「整份产物一个 contract 都没有」= 契约层没写，不是「写错了」。这与「有契约但不给
        # 这个角色入口」是两件事：前者是缺输入（INCOMPLETE），后者才是 ERROR。
        # 混成一件事的后果：example-03/04（写于契约层之前）会被判成「角色没地方干活」，
        # 而读者看到的结论会是「示例错了」，真去改示例 —— 修的却是判据的适用范围。
        rchk("R3", False, "",
             f"全部 {len(_pages)} 个页面都没有 `contract`：R3 靠 `contract.actor` / `owns` 判"
             f"「以它为主体且能进入」，无从判")
        rchk("R3-b", False, "", "同上：无 contract 就无 `owns`，独立待办页判不了")
    else:
        _gap = []
        for r in _roles:
            ok = False
            for p in _pages:
                ct = p.get("contract") or {}
                if r not in (ct.get("actor") or []):
                    continue
                task_ok = any(r in (tk.get("actor") or []) and p.get("id") in (tk.get("pages") or [])
                              for tk in _tasks)
                entry_ok = bool(p.get("entryFrom")) or p.get("id") in _root_ids
                if task_ok and entry_ok:
                    ok = True
                    break
            if not ok:
                _gap.append(r)
        rchk("R3", not _gap,
             f"角色待办覆盖：{' '.join('✗' if r in _gap else '✓' for r in _roles)}"
             f"（{len(_roles) - len(_gap)}/{len(_roles)}）；缺：{', '.join(_gap)} —— "
             f"有命令、但没有一个页面以它为主体且能被它进入")

        # R3-b（Owner 2026-10-27 裁定）：有提交命令的角色必须有**独立待办页**，
        # 「从别人的单据页借道」不算。
        _subs = [c for c in _caps if c.get("stage") == "submit"]
        if not any(c.get("stage") for c in _caps):
            rchk("R3-b", False, "",
                 "`capabilities[].stage` 全为空：分不出「提交类命令」，独立待办页判不了（前置 R4）")
        elif not _subs:
            rchk("R3-b", False, "", "没有任何 stage='submit' 的命令：无对象可判")
        else:
            _gap_b = []
            for r in _roles:
                _my = [c for c in _subs if r in (c.get("actor") or [])]
                if not _my:
                    continue
                _my_ids = {c.get("id") for c in _my}
                ok = False
                for p in _pages:
                    ct = p.get("contract") or {}
                    if r not in (ct.get("actor") or []):
                        continue
                    entry_ok = bool(p.get("entryFrom")) or p.get("id") in _root_ids
                    if _my_ids <= set(ct.get("owns") or []) and entry_ok:
                        ok = True
                        break
                if not ok:
                    _gap_b.append(f"{r} 的 {len(_my_ids)} 条提交命令分散在别人为主体的页面上")
            rchk("R3-b", not _gap_b, "独立待办页：" + "；".join(_gap_b[:4]))

    # ---------------- R4 执行 / 验证双环节 ----------------
    if not _ones:
        for rid in ("R4-a", "R4-b", "R4-c", "R4-d"):
            rchk(rid, False, "",
                 "`dataModel.relations` 里没有 kind='1:N'：R4 的适用范围（措施/任务类实体）为空，"
                 "四条无从判")
    else:
        _bad_a, _bad_b2, _bad_c2, _bad_d3 = [], [], [], []
        for r in _ones:
            ent = r.get("to")
            _sub = [c for c in _caps if c.get("entity") == ent and c.get("stage") == "submit"]
            _ver = [c for c in _caps if c.get("entity") == ent and c.get("stage") == "verify"]
            if not _sub:
                _bad_a.append(f"{ent} 没有 stage='submit' 的命令")
            if not _ver:
                _bad_a.append(f"{ent} 没有 stage='verify' 的命令")
            for v in _ver:
                for s in _sub:
                    sa, va = set(s.get("actor") or []), set(v.get("actor") or [])
                    if sa & va:
                        if not v.get("sameActorOk"):
                            _bad_b2.append(
                                f"{v.get('id')} 与 {s.get('id')} 的 actor 有交集"
                                f"（{sorted(sa & va)}）且未声明 sameActorOk")
                        elif not (v.get("reason") or "").strip():
                            _bad_b2.append(f"{v.get('id')} 写了 sameActorOk 但没写 reason（例外无效）")
                    if s.get("to") not in (v.get("from") or []):
                        _bad_c2.append(f"{v.get('id')}.from 不含 {s.get('id')}.to「{s.get('to')}」")
                _has_eff = bool([e for e in (v.get("effects") or []) if isinstance(e, dict)])
                _has_par = any("parentEffect" in sm for sm in _sms if sm.get("entity") == ent)
                if not (_has_eff or _has_par):
                    _bad_d3.append(
                        f"{v.get('id')} 生效后没有 effects[] 指向主实体，状态机里也没有 parentEffect")
        rchk("R4-a", not _bad_a, "双环节齐全：" + "；".join(_bad_a[:4]))
        rchk("R4-b", not _bad_b2, "角色不同：" + "；".join(_bad_b2[:4]))
        rchk("R4-c", not _bad_c2, "状态衔接：" + "；".join(_bad_c2[:4]))
        rchk("R4-d", not _bad_d3, "主单据联动：" + "；".join(_bad_d3[:4]), warn_only=True)

    _n_pass = sum(1 for _, s in _rst if s == "PASS")
    _n_err = sum(1 for _, s in _rst if s == "ERROR")
    _n_inc = sum(1 for _, s in _rst if s == "INCOMPLETE")
    _n_warn = sum(1 for _, s in _rst if s == "WARN")
    _inc_ids = sorted({rid for rid, s in _rst if s == "INCOMPLETE"})
    # 把逐条状态挂到 rep 上：自证脚本要按 rid 断言"目标判据变红了、别的没变"，
    # 从打印文本里正则捞状态是脆的（文案一改就失配）。
    rep.r_group = list(_rst)
    rep.info(f"R 组（13）：判定 {len(_rst)} 条 → PASS={_n_pass} / ERROR={_n_err} / "
             f"INCOMPLETE={_n_inc} / WARN={_n_warn}"
             + (f"｜未判：{', '.join(_inc_ids)}" if _inc_ids else ""))

    # SS-01：声明侧判据（references/04 §6.8）。放在 R 组之后 —— 几何判据量像素，
    # 这条量「声明有没有落地」，两者互补，互不替代。
    check_props_contract(data, rep)


def run(paths, as_json=False, profile="default", require_r=False):
    strict = profile == "delivery"
    results = []
    worst = 0
    for p in paths:
        if not os.path.exists(p):
            rep = Report(p, profile)
            rep.error("文件不存在")
            results.append(rep)
            worst = 1
            continue
        rep = Report(p, profile)
        try:
            data = load_data(p)
        except Exception as e:
            rep.error(f"解析失败：{e}")
            results.append(rep)
            worst = 1
            continue
        try:
            validate(data, rep, strict=strict)
        except Exception as e:
            rep.error(f"校验过程异常：{e}")
        if rep.errors:
            worst = 1
        # R 组（R1–R4）的 INCOMPLETE 默认**不**让退出码非 0，原因不是"放过它"，而是：
        # 存量产物（含全部示例）写于 R1–R4 之前，没有 fieldRegistry / sourceTerms / relations；
        # 要求它们立刻齐备只会让人关掉检查。真正要求 R 组合格的场景用 `--require-r`
        # （`check_release.py` 的 DoD 12 就是那样调的），那时 INCOMPLETE 与非 0 退出等价。
        if require_r and rep.incomplete_msgs:
            worst = 1
        # SS-01 的 INCOMPLETE 是工具链缺失（契约缺失/不同步），与交付档无关：
        # 判据自己没装好，任何档都不许算过（XX-050 裁定）。
        if rep.toolchain_fail:
            worst = 1
        results.append(rep)

    if as_json:
        out = [{"target": r.target, "profile": r.profile,
                "errors": r.errors, "warns": r.warns, "infos": r.infos,
                "incomplete": r.incomplete_msgs,
                "toolchain_fail": getattr(r, "toolchain_fail", False)}
               for r in results]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return worst

    for r in results:
        print("=" * 68)
        print(f"目标：{r.target}")
        for i in r.infos:
            print(f"  · {i}")
        for w in r.warns:
            print(f"  WARN  {w}")
        for m in r.incomplete_msgs:
            print(f"  INCOMPLETE {m}")
        for e in r.errors:
            print(f"  ERROR {e}")
        if r.errors:
            status = "FAIL"
        elif r.incomplete_msgs:
            status = "INCOMPLETE（有判据判不了，不算通过）"
        elif r.warns:
            status = "PASS(with warnings)"
        else:
            status = "PASS"
        print(f"  => {status}  (errors={len(r.errors)}, warnings={len(r.warns)}, "
              f"incomplete={len(r.incomplete_msgs)}, profile={r.profile})")
    total_inc = sum(len(r.incomplete_msgs) for r in results)
    _toolchain = any(getattr(r, "toolchain_fail", False) for r in results)
    print("=" * 68)
    if any(r.errors for r in results):
        _verdict = "存在 ERROR，必须修复后交付"
    elif _toolchain:
        _verdict = "判据工具链不可用（SS-01 契约缺失或与容器不同步），不算通过"
    else:
        _verdict = "全部通过结构校验"
    print(f"结论（profile={profile}）：" + _verdict
          + (f"｜INCOMPLETE={total_inc} 条（判据在但输入缺，"
             + ("--require-r 下视为不可交付）" if require_r else "默认不拦，但不许当 PASS）")
             if total_inc else ""))
    return worst


if __name__ == "__main__":
    argv = sys.argv[1:]
    as_json = "--json" in argv
    require_r = "--require-r" in argv
    profile = "default"
    args = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--json", "--require-r"):
            pass
        elif a.startswith("--profile="):
            profile = a.split("=", 1)[1].strip()
        elif a == "--profile" and i + 1 < len(argv):
            i += 1
            profile = argv[i]
        else:
            args.append(a)
        i += 1
    if profile not in PROFILES:
        print(f"未知 --profile={profile}；可用：{list(PROFILES)}", file=sys.stderr)
        sys.exit(2)
    if not args:
        print(__doc__)
        sys.exit(2)
    sys.exit(run(args, as_json, profile, require_r))
