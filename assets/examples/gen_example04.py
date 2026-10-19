#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 example-04-master-detail.json —— 「主子表（MasterDetail）」全链路 few-shot。

场景取自真实 B2B 中后台截图：设备巡检管理系统的「巡检任务管理」页。
- 主表：巡检任务（任务编号 / 状态 / 任务名称 / 巡检计划 / 巡检标准 / 车间 / 线体 / 物资名称）
- 子表：巡检项（点主表某一行 → 子表按 taskNo 过滤出该任务的巡检项）
- 子表可展开收起；主表行用单选圆点标记「当前行」

改数据请改本脚本再重跑，不要手改 JSON：
    python3 gen_example04.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "example-04-master-detail.json")

# ---------------------------------------------------------------- 主表数据
TASKS = [
    ("ONSETE-20261016-0043", "巡检中", "巡检072001/2026-10-16 10:00:00", "巡检072001", "xunj", "四车间", "16产线", "三元材料"),
    ("ONSETE-20261016-0042", "巡检中", "0422pln/2026-10-16 10:00:00", "0422pln", "xunj", "四车间", "16产线", "三元材料"),
    ("ONSETE-20261016-0041", "巡检中", "巡检072001/2026-10-16 09:00:00", "巡检072001", "xunj", "四车间", "16产线", "三元材料"),
    ("ONSETE-20261016-0040", "已完成", "巡检072001/2026-10-16 09:00:00", "巡检072001", "xunj", "四车间", "16产线", "三元材料"),
    ("ONSETE-20261016-0039", "巡检中", "0422pln/2026-10-16 09:00:00", "0422pln", "xunj", "四车间", "16产线", "三元材料"),
    ("ONSETE-20261016-0038", "已完成", "0422pln/2026-10-16 09:00:00", "0422pln", "xunj", "四车间", "16产线", "三元材料"),
    ("ONSETE-20261016-0037", "巡检中", "csdp/2026-10-16 08:00:00", "csdp", "测试断批", "四车间", "13产线", "三元材料"),
    ("ONSETE-20261016-0036", "巡检中", "XJ0911/2026-10-16 08:00:00", "XJ0911", "巡检标准名称004", "办公楼", "综合库(办公楼)", "三元材料"),
]
# 已作废一条，用来演示「作废任务不可修改」这条需求
TASKS.append(("ONSETE-20261016-0035", "已作废", "XJ0911/2026-10-16 08:00:00", "XJ0911", "巡检标准名称004", "办公楼", "综合库(办公楼)", "三元材料"))

TASK_ROWS = [
    {"no": no, "status": st, "name": nm, "plan": pl, "standard": sd,
     "workshop": ws, "line": ln, "material": mt}
    for (no, st, nm, pl, sd, ws, ln, mt) in TASKS
]

# ---------------------------------------------------------------- 子表数据
# taskNo 对应主表的 no；后两条任务故意不给明细，用来演示子表空态
ITEMS = [
    ("XJ-20251209002", "测试巡检项目 01;", "方法", "1", "小时", 1, "一次配混", "一次配混", "待巡检", "-", "", ""),
    ("XJ-20251209003", "三元材料外观无结块、无变色", "目测", "2", "小时", 2, "一次配混", "出料", "合格", "外观正常", "IMG-0031.jpg", ""),
    ("XJ-20251209004", "包装袋封口强度抽检", "拉力计", "1", "班次", 3, "包装", "封口", "待巡检", "-", "", ""),
]
ITEM_ROWS_1 = [dict(zip(
    ["no", "content", "method", "freqDim", "freqUnit", "freqTimes", "process", "step", "status", "result", "images", "videos"],
    it)) | {"taskNo": "ONSETE-20261016-0043"} for it in ITEMS]

ITEMS2 = [
    ("XJ-20251209011", "投料前核对物料批次号与随工单一致", "核对", "1", "班次", 1, "一次配混", "投料", "合格", "批次一致", "", ""),
    ("XJ-20251209012", "混料机转速记录与设定值偏差", "查记录", "4", "小时", 2, "一次配混", "混料", "待巡检", "-", "", ""),
]
ITEM_ROWS_2 = [dict(zip(
    ["no", "content", "method", "freqDim", "freqUnit", "freqTimes", "process", "step", "status", "result", "images", "videos"],
    it)) | {"taskNo": "ONSETE-20261016-0042"} for it in ITEMS2]

ITEMS3 = [
    ("XJ-20251209021", "成品水分含量检测", "水分仪", "1", "小时", 4, "干燥", "出料", "待巡检", "-", "", ""),
]
ITEM_ROWS_3 = [dict(zip(
    ["no", "content", "method", "freqDim", "freqUnit", "freqTimes", "process", "step", "status", "result", "images", "videos"],
    it)) | {"taskNo": "ONSETE-20261016-0041"} for it in ITEMS3]

ITEM_ROWS = ITEM_ROWS_1 + ITEM_ROWS_2 + ITEM_ROWS_3

# ---------------------------------------------------------------- 组件树
def master_table():
    return {
        "id": "n-task-table", "type": "Table",
        "props": {
            "title": "巡检任务",
            "radio": True,                    # 单选圆点：标记「当前行」
            "size": "small",
            "query": [
                {"label": "任务编号", "type": "Input", "placeholder": "请输入任务编号"},
                {"label": "状态", "type": "Select", "placeholder": "请选择",
                 "props": {"options": [{"value": "pending", "label": "待巡检"},
                                       {"value": "doing", "label": "巡检中"},
                                       {"value": "done", "label": "已完成"},
                                       {"value": "void", "label": "已作废"}]}},
                {"label": "车间", "type": "Select", "placeholder": "请选择",
                 "props": {"options": [{"value": "ws4", "label": "四车间"},
                                       {"value": "office", "label": "办公楼"}]}},
            ],
            "toolbar": [
                {"text": "新增", "type": "primary", "icon": "plus", "id": "n-btn-new"},
                {"text": "导出", "icon": "download", "id": "n-btn-export"},
                {"text": "发布任务", "disabled": True},
                {"text": "废弃", "disabled": True},
            ],
            "columns": [
                {"title": "序号", "type": "index", "width": "56px"},
                {"title": "任务编号", "dataIndex": "no", "width": "190px"},
                {"title": "状态", "dataIndex": "status", "type": "tag", "width": "90px"},
                {"title": "任务名称", "dataIndex": "name", "width": "220px"},
                {"title": "巡检计划", "dataIndex": "plan", "width": "120px"},
                {"title": "巡检标准", "dataIndex": "standard", "width": "130px"},
                {"title": "车间", "dataIndex": "workshop", "width": "90px"},
                {"title": "线体", "dataIndex": "line", "width": "140px"},
                {"title": "物资名称", "dataIndex": "material", "width": "110px"},
                {"title": "操作", "type": "action", "width": "150px",
                 "actions": [{"key": "detail", "label": "详情"},
                             {"key": "edit", "label": "修改"},
                             {"key": "del", "label": "删除", "type": "danger"}]},
            ],
            "data": TASK_ROWS,
            "pagination": {"total": 36927, "pageSize": 10, "current": 1, "jump": True},
        },
    }


def detail_table():
    return {
        "id": "n-item-table", "type": "Table",
        "props": {
            "title": "巡检项",
            "size": "small",
            "emptyText": "该任务暂无巡检项",
            "columns": [
                {"title": "序号", "type": "index", "width": "56px"},
                {"title": "巡检项编号", "dataIndex": "no", "width": "150px"},
                {"title": "巡检内容", "dataIndex": "content", "width": "260px"},
                {"title": "巡检方法", "dataIndex": "method", "width": "100px"},
                {"title": "检验频次维度", "dataIndex": "freqDim", "width": "110px"},
                {"title": "频次维度单位", "dataIndex": "freqUnit", "width": "110px"},
                {"title": "检验频次次数", "dataIndex": "freqTimes", "width": "110px"},
                {"title": "工序", "dataIndex": "process", "width": "110px"},
                {"title": "工步", "dataIndex": "step", "width": "110px"},
                {"title": "巡检状态", "dataIndex": "status", "type": "tag", "width": "100px"},
                {"title": "巡检结果", "dataIndex": "result", "width": "110px"},
                {"title": "巡检图片", "dataIndex": "images", "width": "120px"},
                {"title": "视频", "dataIndex": "videos", "width": "80px"},
            ],
            "data": ITEM_ROWS,
        },
    }


def edit_drawer():
    """中等复杂度编辑 → 抽屉（不是对话框）。契约见 references/08-container-choice.md §3.1。"""
    def fi(nid, label, ctl, required=False):
        return {"id": nid, "type": "FormItem",
                "props": {"label": label, "required": required},
                "children": [ctl]}
    return {
        "id": "n-dr-edit", "type": "Drawer",
        "props": {"modalId": "dr-edit", "title": "修改巡检任务", "open": False,
                  "placement": "right", "width": 520},
        "children": [{
            "id": "n-dr-form", "type": "Form", "props": {"layout": "vertical"},
            "children": [
                fi("n-f-no", "任务编号", {"id": "n-i-no", "type": "Input",
                                          "props": {"value": "ONSETE-20261016-0043", "disabled": True}}),
                fi("n-f-name", "任务名称", {"id": "n-i-name", "type": "Input",
                                            "props": {"value": "巡检072001/2026-10-16 10:00:00"}}, True),
                fi("n-f-plan", "巡检计划", {"id": "n-i-plan", "type": "Select",
                                            "props": {"value": "巡检072001",
                                                      "options": [{"value": "巡检072001", "label": "巡检072001"},
                                                                  {"value": "0422pln", "label": "0422pln"}]}}),
                fi("n-f-ws", "车间", {"id": "n-i-ws", "type": "Select",
                                      "props": {"value": "四车间",
                                                "options": [{"value": "四车间", "label": "四车间"},
                                                            {"value": "办公楼", "label": "办公楼"}]}}),
                fi("n-f-line", "线体", {"id": "n-i-line", "type": "Input", "props": {"value": "16产线"}}),
                fi("n-f-at", "计划时间", {"id": "n-i-at", "type": "DatePicker",
                                          "props": {"value": "2026-10-16 10:00"}}),
                fi("n-f-remark", "备注", {"id": "n-i-remark", "type": "TextArea",
                                          "props": {"placeholder": "选填，最多 200 字", "maxLength": 200,
                                                    "showCount": True}}),
                {"id": "n-dr-btns", "type": "Space",
                 "children": [
                     {"id": "n-btn-cancel", "type": "Button", "props": {"text": "取消"}},
                     {"id": "n-btn-submit", "type": "Button", "props": {"text": "保存", "type": "primary"}},
                 ]},
            ],
        }],
    }


def del_modal():
    return {
        "id": "n-modal-del", "type": "Modal",
        "props": {"modalId": "m-del", "title": "删除巡检任务", "open": False,
                  "content": "删除后该任务及其巡检项将不可恢复，确认删除？",
                  "okText": "删除", "cancelText": "取消"},
    }


def page_task_list():
    return {
        "id": "page-inspect-task", "name": "巡检任务管理", "route": "/inspect/task",
        "moduleId": "m-inspect",
        "goal": "在一个页面里同时看清「任务」与「该任务的巡检项」，不用来回跳页。",
        "componentTree": {
            "id": "n-root", "type": "Layout", "props": {"layout": "header-content"},
            "children": [
                {"id": "n-header", "type": "Header", "props": {"title": "现场巡检任务管理"}},
                {"id": "n-content", "type": "Content", "children": [
                    {"id": "n-md-task", "type": "MasterDetail",
                     "props": {"bind": "no", "bindTo": "taskNo",
                               "detailTitle": "巡检项", "collapsible": True,
                               "autoSelectFirst": True, "defaultCollapsed": False,
                               "emptyText": "请先在上方选择一条巡检任务"},
                     "children": [master_table(), detail_table()]},
                    edit_drawer(),
                    del_modal(),
                ]},
            ],
        },
        "states": [
            {"id": "s-default", "name": "默认态", "description": "默认：主表有数据、子表显示首行明细",
             "vars": {"taskNo": "ONSETE-20261016-0043"}, "overrides": []},
            {"id": "s-loading", "name": "加载态", "description": "加载中：主表骨架屏",
             "vars": {},
             "overrides": [{"target": "n-task-table", "prop": "loading", "value": True}]},
            {"id": "s-empty", "name": "空态", "description": "空：筛选后无任务，子表无明细",
             "vars": {},
             "overrides": [{"target": "n-task-table", "prop": "data", "value": []},
                           {"target": "n-item-table", "prop": "data", "value": []}]},
            {"id": "s-error", "name": "异常态", "description": "异常：巡检服务不可用，主表降级为错误提示",
             "vars": {},
             "overrides": [{"target": "n-task-table", "prop": "emptyText",
                            "value": "巡检服务暂时不可用，请稍后重试（错误码 INS-503）"},
                           {"target": "n-task-table", "prop": "data", "value": []}]},
        ],
        "defaultStateId": "s-default",
        "interactions": [
            {"id": "ix-detail", "name": "查看任务详情（带参跳转）",
             "on": {"event": "click", "target": "n-task-table__act_*_detail"},
             "actions": [{"type": "navigate", "pageId": "page-inspect-task-detail",
                          "params": {"taskNo": "{{row.no}}", "taskName": "{{row.name}}"}}]},
            {"id": "ix-edit", "name": "打开修改抽屉",
             "on": {"event": "click", "target": "n-task-table__act_*_edit"},
             "conditions": [{"left": "row.status", "op": "!=", "right": "已作废"}],
             "actions": [{"type": "showDrawer", "drawerId": "dr-edit"}]},
            {"id": "ix-edit-void", "name": "作废任务不可修改",
             "on": {"event": "click", "target": "n-task-table__act_*_edit"},
             "conditions": [{"left": "row.status", "op": "==", "right": "已作废"}],
             "actions": [{"type": "message", "level": "warning", "text": "已作废的任务不可修改"}]},
            {"id": "ix-del", "name": "删除确认",
             "on": {"event": "click", "target": "n-task-table__act_*_del"},
             "actions": [{"type": "showModal", "modalId": "m-del"}]},
            {"id": "ix-del-ok", "name": "确认删除",
             "on": {"event": "click", "target": "n-modal-del__ok"},
             "actions": [{"type": "hideModal", "modalId": "m-del"},
                         {"type": "message", "level": "success", "text": "任务已删除"}]},
            {"id": "ix-cancel", "name": "关闭修改抽屉",
             "on": {"event": "click", "target": "n-btn-cancel"},
             "actions": [{"type": "hideDrawer", "drawerId": "dr-edit"}]},
            {"id": "ix-submit", "name": "保存修改",
             "on": {"event": "click", "target": "n-btn-submit"},
             "actions": [{"type": "hideDrawer", "drawerId": "dr-edit"},
                         {"type": "message", "level": "success", "text": "已保存"}]},
        ],
        "annotations": [
            {"id": "an-1", "anchor": {"nodeId": "n-md-task", "x": 0.5, "y": 0.5},
             "text": "子表默认展开首行明细；若任务很多，希望支持「默认全部收起」以加快首屏扫描。",
             "category": "interaction", "author": "PM", "status": "open",
             "createdAt": "2026-10-16T11:00:00+08:00", "replies": []},
        ],
        "entryFrom": ["page-inspect-task-detail"],
        "exitTo": ["page-inspect-task-detail"],
        "prd": {
            "summary": "巡检任务管理是「现场巡检」模块的主工作台：上方是任务清单，下方是选中任务的巡检项。",
            "reqIds": ["REQ-INSPECT-001", "REQ-INSPECT-002", "REQ-INSPECT-003", "REQ-INSPECT-004", "REQ-INSPECT-005"],
            "sections": [
                {"id": "sec-goal", "heading": "页面目标",
                 "body": "在一个页面里同时看清「任务」与「该任务的巡检项」，不用来回跳页。\n\n"
                         "适用场景：单条主记录下挂着若干明细（一条巡检任务 → 若干巡检项），"
                         "用户需要**边扫主表、边看某一条的明细**。"},
                {"id": "sec-flow", "type": "flow", "heading": "主流程：从任务清单到巡检项",
                 "caption": "任务列表：选中行 → 子表联动 → 详情页 / 修改抽屉",
                 "dir": "LR",
                 "nodes": [
                     {"id": "s1", "label": "进入巡检任务管理", "sub": "/inspect/task", "kind": "start"},
                     {"id": "s2", "label": "主表默认选中首行", "sub": "子表自动联动"},
                     {"id": "s3", "label": "点其它行", "sub": "子表按 taskNo 过滤"},
                     {"id": "s4", "label": "任务是否已作废？", "kind": "decision"},
                     {"id": "s5", "label": "提示不可修改", "sub": "仅「详情」可用", "kind": "warn"},
                     {"id": "s6", "label": "打开修改抽屉", "sub": "dr-edit"},
                     {"id": "s7", "label": "跳转任务详情页", "sub": "/inspect/task/:taskNo", "kind": "end"},
                 ],
                 "edges": [
                     {"from": "s1", "to": "s2"}, {"from": "s2", "to": "s3"},
                     {"from": "s3", "to": "s4"},
                     {"from": "s4", "to": "s5", "label": "已作废"},
                     {"from": "s4", "to": "s6", "label": "可修改"},
                     {"from": "s3", "to": "s7", "label": "点「详情」"},
                 ]},
                {"id": "sec-struct", "heading": "页面结构",
                 "body": "```\nLayout(header-content)\n"
                         "├─ Header  现场巡检任务管理\n"
                         "└─ Content\n"
                         "   ├─ MasterDetail  n-md-task\n"
                         "   │  ├─ Table  巡检任务（主表，radio 单选行）\n"
                         "   │  └─ Table  巡检项（子表，按 taskNo 过滤）\n"
                         "   ├─ Drawer  dr-edit  修改巡检任务\n"
                         "   └─ Modal   m-del    删除确认\n```\n\n"
                         "**主子表是本页的核心结构**：主表与子表在同一个 `MasterDetail` 里，"
                         "共享一次页面加载，点行即联动，不做二次请求。"},
                {"id": "sec-ix", "heading": "交互说明",
                 "body": "1. **选中主表行**：点主表任意一行的非操作列区域 → 该行加单选圆点并高亮（浅蓝底），"
                         "子表立即按 `taskNo` 过滤出该任务的巡检项，标题右侧显示「共 N 条」。\n"
                         "2. **子表展开/收起**：点子表标题栏（或左侧 ▾ 箭头）折叠；再点展开。"
                         "点主表某行会**自动展开**子表，避免「选了行却看不到明细」。\n"
                         "3. **空明细**：该任务没有巡检项时，子表区显示「该任务暂无巡检项」，"
                         "而不是留一片空白。\n"
                         "4. **详情**：点操作列「详情」→ 跳转任务详情页，URL 带上 `taskNo`。\n"
                         "5. **修改**：点操作列「修改」→ 右侧滑出抽屉 `dr-edit`（保留主表筛选与滚动位置）。\n"
                         "6. **删除**：点操作列「删除」→ 弹出确认对话框 `m-del`，强模态确认后才删除。\n"
                         "7. **作废任务**：状态为「已作废」的任务，「修改」只提示不可修改，「详情」仍可查看。"},
                {"id": "sec-rules", "heading": "业务规则",
                 "body": "- 主表每行有且仅有一条被选中；不允许「一行都不选」（默认选中首行）。\n"
                         "- 子表数据由 `taskNo` 与主表 `no` 关联，禁止把全部巡检项平铺在子表里。\n"
                         "- 任务状态为「已作废」时，禁止修改；删除需要二次确认。\n"
                         "- 主表分页每页 10 条，总数与分页器一致（演示值 36927）。\n"
                         "- 车间 / 线体 / 物资名称来自基础数据，不在本页维护。"},
                {"id": "sec-states", "heading": "页面状态",
                 "body": "| 状态 | 表现 |\n|---|---|\n"
                         "| 默认态 | 主表 9 条任务，子表显示首行的巡检项 |\n"
                         "| 加载态 | 主表骨架屏，子表暂不渲染 |\n"
                         "| 空态 | 主表「暂无数据」，子表同步清空 |\n"
                         "| 异常态 | 主表提示「巡检服务暂时不可用（INS-503）」，保留筛选条件 |"},
                {"id": "sec-accept", "heading": "验收条件",
                 "body": "- [ ] 进入页面默认选中首行，子表立即显示该任务的巡检项\n"
                         "- [ ] 点其它行后，子表内容与选中行一致，且标题显示正确的条数\n"
                         "- [ ] 子表可折叠、可再展开；点主表行会自动展开子表\n"
                         "- [ ] 无明细的任务显示空态文案，不留空白\n"
                         "- [ ] 「详情」跳转后 URL 携带 taskNo，刷新仍停在该页\n"
                         "- [ ] 「已作废」任务点「修改」只提示，不打开抽屉\n"
                         "- [ ] 删除必须经过确认对话框，取消不改数据"},
            ],
        },
    }


def page_task_detail():
    return {
        "id": "page-inspect-task-detail", "name": "巡检任务详情", "route": "/inspect/task/:taskNo",
        "moduleId": "m-inspect", "parentId": "page-inspect-task",
        "goal": "完整查看一条巡检任务的信息、巡检项与流转记录，并在此发起审批类操作。",
        "componentTree": {
            "id": "n-d-root", "type": "Layout", "props": {"layout": "header-content"},
            "children": [
                {"id": "n-d-header", "type": "Header",
                 "props": {"title": "巡检任务详情", "back": True}},
                {"id": "n-d-content", "type": "Content", "children": [
                    {"id": "n-d-desc", "type": "Descriptions",
                     "props": {"title": "任务信息", "column": 3, "items": [
                         {"label": "任务编号", "value": "{{taskNo}}"},
                         {"label": "任务名称", "value": "{{taskName}}"},
                         {"label": "状态", "value": "巡检中"},
                         {"label": "巡检计划", "value": "巡检072001"},
                         {"label": "巡检标准", "value": "xunj"},
                         {"label": "车间 / 线体", "value": "四车间 / 16产线"},
                         {"label": "物资名称", "value": "三元材料"},
                         {"label": "计划时间", "value": "2026-10-16 10:00"},
                         {"label": "创建人", "value": "李巡检"},
                     ]}},
                    {"id": "n-d-actions", "type": "Space", "props": {"style": "margin:12px 0"}, "children": [
                        {"id": "n-d-btn-back", "type": "Button", "props": {"text": "返回列表", "icon": "arrow-left"}},
                        {"id": "n-d-btn-done", "type": "Button", "props": {"text": "标记完成", "type": "primary"}},
                    ]},
                    {"id": "n-d-timeline", "type": "Timeline", "props": {"items": [
                        {"title": "创建任务", "description": "李巡检 · 2026-10-16 08:00"},
                        {"title": "开始巡检", "description": "李巡检 · 2026-10-16 10:02"},
                        {"title": "提交巡检结果", "description": "李巡检 · 2026-10-16 10:35"},
                    ]}},
                ]},
            ],
        },
        "states": [
            {"id": "s-default", "name": "默认态", "description": "默认：展示任务信息与流转记录",
             "vars": {"taskNo": "ONSETE-20261016-0043", "taskName": "巡检072001/2026-10-16 10:00:00"},
             "overrides": []},
            {"id": "s-loading", "name": "加载态", "description": "加载中：信息区骨架屏",
             "vars": {},
             "overrides": [{"target": "n-d-desc", "prop": "loading", "value": True}]},
            {"id": "s-error", "name": "异常态", "description": "异常：任务不存在或已删除",
             "vars": {}, "overrides": [{"target": "n-d-timeline", "prop": "items", "value": []}]},
        ],
        "defaultStateId": "s-default",
        "notApplicableStates": ["empty"],
        "interactions": [
            {"id": "ix-d-back", "name": "返回列表",
             "on": {"event": "click", "target": "n-d-btn-back"},
             "actions": [{"type": "back"}]},
            {"id": "ix-d-done", "name": "标记完成",
             "on": {"event": "click", "target": "n-d-btn-done"},
             "actions": [{"type": "message", "level": "success", "text": "任务已标记完成"}]},
        ],
        "annotations": [],
        "entryFrom": ["page-inspect-task"],
        "exitTo": ["page-inspect-task"],
        "prd": {
            "summary": "任务详情页承载单条巡检任务的全量信息与流转记录，是「长时间停留」的工作台，因此用独立页面而非对话框。",
            "reqIds": ["REQ-INSPECT-006"],
            "sections": [
                {"id": "sec-goal", "heading": "页面目标",
                 "body": "完整查看一条巡检任务的信息、巡检项与流转记录，并在此发起审批类操作。\n\n"
                         "**为什么是独立页面而不是对话框**：详情含关联信息 + 时间线 + 多个操作入口，"
                         "对话框展不开；抽屉在需要长时间停留时信息密度也不够。"
                         "详见 `references/08-container-choice.md` §3.2。"},
                {"id": "sec-flow", "type": "flow", "heading": "主流程：从列表进入详情",
                 "caption": "列表页「详情」→ 带参跳转 → 详情页 → 返回列表",
                 "dir": "LR",
                 "nodes": [
                     {"id": "d1", "label": "任务列表点「详情」", "sub": "带 taskNo", "kind": "start"},
                     {"id": "d2", "label": "渲染任务信息", "sub": "{{taskNo}} / {{taskName}}"},
                     {"id": "d3", "label": "渲染流转记录", "sub": "Timeline"},
                     {"id": "d4", "label": "点「返回列表」", "sub": "n-d-btn-back", "kind": "end"},
                 ],
                 "edges": [{"from": "d1", "to": "d2"}, {"from": "d2", "to": "d3"}, {"from": "d3", "to": "d4"}],
                 },
                {"id": "sec-ix", "heading": "交互说明",
                 "body": "1. 顶部「← 返回」与「返回列表」都回到任务列表页，**不跳出容器**。\n"
                         "2. 页面用 `{{taskNo}}` / `{{taskName}}` 渲染来源列表的选中行；"
                         "直接打开该页时用 `states[].vars` 的默认值，保证可独立渲染。\n"
                         "3. 时间线按时间正序展示流转记录。"},
                {"id": "sec-rules", "heading": "业务规则",
                 "body": "- 只有「巡检中」的任务可以「标记完成」。\n"
                         "- 流转记录保留 180 天。\n"
                         "- 任务不存在时展示异常态，并给回列表的入口。"},
                {"id": "sec-states", "heading": "页面状态",
                 "body": "| 状态 | 表现 |\n|---|---|\n"
                         "| 默认态 | 信息区 + 操作区 + 时间线 |\n"
                         "| 加载态 | 信息区骨架屏 |\n"
                         "| 异常态 | 任务不存在，时间线为空，提示返回列表 |"},
                {"id": "sec-accept", "heading": "验收条件",
                 "body": "- [ ] 从列表点「详情」后，任务编号与名称与所点行一致\n"
                         "- [ ] 直接打开 `/inspect/task/ONSETE-20261016-0043` 能正常渲染（有默认值）\n"
                         "- [ ] 点「返回」回到列表页，仍在容器内\n"
                         "- [ ] 时间线展示全部流转记录"},
            ],
        },
    }


# ---------------------------------------------------------------- 组装
data = {
    "meta": {"schemaVersion": "1.0", "product": "设备巡检管理系统", "version": "1.0.0",
             "createdAt": "2026-10-16T10:00:00+08:00", "updatedAt": "2026-10-16T11:30:00+08:00",
             "reviewMode": False, "currentPageId": "page-inspect-task", "defaultPanel": "both"},
    "product": {
        "name": "设备巡检管理系统",
        "oneLiner": "让车间巡检员在 3 分钟内完成一轮现场巡检任务的执行与结果登记",
        "positioning": "面向流程制造车间的巡检管理工具。以「一条任务挂多条巡检项」为主从结构，"
                       "把纸质巡检表搬到线上，用状态机保证巡检结果不可跳过、不可漏项。",
        "targetUsers": ["现场巡检员", "质量主管"],
        "coreValue": "把「漏检」从不可控变成可查：每一行巡检项都有状态、有结果、有留痕",
        "nonGoals": ["不做设备台账与备件管理", "不做移动端离线巡检", "不做检验设备数据直连采集"],
        "metrics": [
            {"name": "单轮巡检登记耗时", "target": "< 3min", "type": "leading"},
            {"name": "巡检任务按期完成率", "target": "> 98%", "type": "lagging"},
            {"name": "漏检项占比", "target": "< 0.5%", "type": "lagging"},
        ],
    },
    "users": [
        {"id": "u-inspector", "name": "现场巡检员",
         "description": "按计划到产线逐项执行巡检并登记结果",
         "goals": ["一眼看到今天要做哪些巡检任务", "点开任务就知道要查哪些项", "结果登记要快"],
         "painPoints": ["纸质巡检表容易漏项", "任务与巡检项对不上号", "结果登记要回头补录"]},
        {"id": "u-qm", "name": "质量主管",
         "description": "对巡检执行情况负责，关注漏检与异常",
         "goals": ["快速找到未完成的任务", "看到哪些巡检项没做", "任务作废要留痕"],
         "painPoints": ["不知道谁漏检了", "任务被随意修改没有记录"]},
    ],
    "userFlows": [
        {"id": "flow-exec", "name": "执行一轮巡检任务", "role": "u-inspector",
         "goal": "把一条巡检任务下的所有巡检项执行完并登记结果",
         "steps": [
             {"id": "st-1", "name": "进入巡检任务管理", "pageId": "page-inspect-task", "note": "默认按计划时间倒序"},
             {"id": "st-2", "name": "在主表选中今天的任务", "pageId": "page-inspect-task", "note": "子表联动出巡检项"},
             {"id": "st-3", "name": "逐项执行并登记结果", "pageId": "page-inspect-task", "note": "在子表内完成"},
             {"id": "st-4", "name": "点「详情」查看完整信息", "pageId": "page-inspect-task-detail", "note": "带 taskNo 跳转"},
             {"id": "st-5", "name": "标记完成并返回列表", "pageId": "page-inspect-task-detail", "note": "返回不跳出容器"},
         ]},
        {"id": "flow-void", "name": "作废一条巡检任务", "role": "u-qm",
         "goal": "把因停线等原因无需执行的巡检任务作废，且不可再被修改",
         "steps": [
             {"id": "st-6", "name": "在列表找到目标任务", "pageId": "page-inspect-task", "note": "按任务编号筛选"},
             {"id": "st-7", "name": "点操作列「删除」", "pageId": "page-inspect-task", "note": "弹确认对话框"},
             {"id": "st-8", "name": "确认后任务不再可修改", "pageId": "page-inspect-task", "note": "点「修改」只提示"},
         ]},
    ],
    "modules": [
        {"id": "m-inspect", "name": "现场巡检",
         "goal": "承载巡检任务的计划、执行、结果登记与查询",
         "priority": "P0", "pageIds": ["page-inspect-task", "page-inspect-task-detail"], "dependsOn": []},
    ],
    "dataModel": {
        "entities": [
            {"id": "e-inspect-task", "name": "InspectTask", "table": "inspect_task",
             "description": "一次巡检计划落到某个车间/线体/物资上的执行单元",
             "pageIds": ["page-inspect-task", "page-inspect-task-detail"],
             "fields": [
                 {"name": "id", "type": "string", "required": True, "key": "pk", "note": "ULID"},
                 {"name": "no", "type": "string", "required": True, "unique": True,
                  "note": "任务编号，如 ONSETE-20261016-0043；主子表关联键"},
                 {"name": "name", "type": "string", "required": True, "note": "任务名称（计划名/计划时间）"},
                 {"name": "status", "type": "enum", "required": True,
                  "constraint": "待巡检|巡检中|已完成|已作废", "note": "见 sm-inspect 状态机"},
                 {"name": "plan", "type": "string", "required": True, "note": "巡检计划名"},
                 {"name": "standard", "type": "string", "required": True, "note": "巡检标准名"},
                 {"name": "workshop", "type": "string", "required": True, "key": "fk", "note": "→ 基础数据.车间"},
                 {"name": "line", "type": "string", "required": True, "note": "线体，如 16产线"},
                 {"name": "material", "type": "string", "required": True, "note": "物资名称，如 三元材料"},
                 {"name": "plannedAt", "type": "datetime", "required": True, "note": "计划时间"},
                 {"name": "createdAt", "type": "datetime", "required": True, "note": ""},
             ],
             "relations": [{"type": "has_many", "target": "e-inspect-item", "via": "no",
                            "note": "一条任务挂多条巡检项（子表）"}],
             "indexes": ["no", "status", "plannedAt"]},
            {"id": "e-inspect-item", "name": "InspectItem", "table": "inspect_item",
             "description": "任务下的单条巡检项（子表行）",
             "pageIds": ["page-inspect-task"],
             "fields": [
                 {"name": "id", "type": "string", "required": True, "key": "pk", "note": ""},
                 {"name": "no", "type": "string", "required": True, "unique": True, "note": "巡检项编号"},
                 {"name": "taskNo", "type": "string", "required": True, "key": "fk",
                  "note": "→ inspect_task.no，主子表关联键"},
                 {"name": "content", "type": "string", "required": True, "note": "巡检内容"},
                 {"name": "method", "type": "string", "required": True, "note": "巡检方法，如 目测/拉力计"},
                 {"name": "freqDim", "type": "number", "required": True, "note": "检验频次维度（数值）"},
                 {"name": "freqUnit", "type": "string", "required": True, "note": "频次维度单位，如 小时/班次"},
                 {"name": "freqTimes", "type": "number", "required": True, "note": "检验频次次数"},
                 {"name": "process", "type": "string", "required": True, "note": "工序"},
                 {"name": "step", "type": "string", "required": True, "note": "工步"},
                 {"name": "status", "type": "enum", "required": True,
                  "constraint": "待巡检|合格|不合格", "note": "巡检状态"},
                 {"name": "result", "type": "string", "required": False, "note": "巡检结果描述"},
                 {"name": "images", "type": "string", "required": False, "note": "巡检图片（文件名，可多张）"},
                 {"name": "videos", "type": "string", "required": False, "note": "巡检视频（文件名）"},
             ],
             "relations": [{"type": "belongs_to", "target": "e-inspect-task", "via": "taskNo",
                            "note": "所属巡检任务"}],
             "indexes": ["taskNo", "status"]},
            {"id": "e-user", "name": "User", "table": "user", "description": "巡检员 / 质量主管",
             "pageIds": ["page-inspect-task", "page-inspect-task-detail"],
             "fields": [
                 {"name": "id", "type": "string", "required": True, "key": "pk", "note": ""},
                 {"name": "name", "type": "string", "required": True, "note": "展示名"},
                 {"name": "role", "type": "enum", "required": True,
                  "constraint": "inspector|qm", "note": "巡检员 / 质量主管"},
             ],
             "relations": [], "indexes": ["name"]},
        ],
        "derived": [
            {"name": "任务巡检项总数", "expr": "count(inspect_item where taskNo = task.no)",
             "fallback": "无明细时展示 0，并显示「该任务暂无巡检项」",
             "usedBy": ["page-inspect-task"], "reqId": "REQ-INSPECT-002"},
            {"name": "任务完成率", "expr": "count(item where status != 待巡检) / count(item)",
             "fallback": "分母为 0 时展示「—」", "usedBy": ["page-inspect-task"],
             "reqId": "REQ-INSPECT-003"},
        ],
    },
    "pages": [page_task_list(), page_task_detail()],
    "components": [
        {"id": "c-md-panel", "name": "主子表面板", "antd": "Table + Table（自研组合）",
         "description": "上方主表、下方子表的复合结构，用于「一条主记录挂多条明细」的场景",
         "anatomy": ["主表工具条", "主表查询条", "主表（含单选列）", "子表标题栏（含折叠箭头 / 条数）", "子表"],
         "variants": [{"name": "展开", "description": "默认，子表可见"},
                      {"name": "收起", "description": "只留子表标题栏，主表占满高度"}],
         "states": ["normal", "row-selected", "empty-detail", "collapsed", "loading"],
         "tokens": {"gap": "14px", "headerHeight": "40px", "radius": "8px"},
         "spec": "子表标题栏必须显示「当前选中行的明细条数」；点主表行必须自动展开子表；"
                 "主表行点选与操作列点击必须互不干扰（操作列按钮不触发选行）。"},
        {"id": "c-status-tag", "name": "任务状态标签", "antd": "Tag",
         "description": "巡检任务状态在全站的统一视觉表达",
         "anatomy": ["色块背景", "状态文字"],
         "variants": [{"name": "待巡检", "description": "默认灰", "token": "default"},
                      {"name": "巡检中", "description": "主色蓝", "token": "processing"},
                      {"name": "已完成", "description": "成功绿", "token": "success"},
                      {"name": "已作废", "description": "中性灰", "token": "default"}],
         "states": ["normal"],
         "tokens": {"radius": "4px", "height": "22px", "fontSize": "12px", "padding": "0 8px"},
         "spec": "状态与颜色严格一一映射；同一任务在列表页与详情页必须使用完全相同的映射。"},
        {"id": "c-query-bar", "name": "查询条件区", "antd": "Form（inline）",
         "description": "列表页顶部的筛选区",
         "anatomy": ["字段标签", "字段控件", "设置查询字段", "搜索按钮", "展开/收起"],
         "variants": [{"name": "收起", "description": "只展示第一行条件"}],
         "states": ["normal", "expanded"],
         "tokens": {"padding": "14px 16px", "gap": "12px 20px"},
         "spec": "「搜索」是主按钮（primary）；「设置查询字段」与「展开」是文字链接，不用按钮样式。"},
    ],
    "stateMachines": [
        {"id": "sm-inspect", "name": "巡检任务状态机", "entity": "InspectTask", "initial": "pending",
         "states": [{"id": "pending", "name": "待巡检", "type": "normal"},
                    {"id": "doing", "name": "巡检中", "type": "normal"},
                    {"id": "done", "name": "已完成", "type": "success"},
                    {"id": "void", "name": "已作废", "type": "disabled"}],
         "transitions": [
             {"id": "t-1", "from": "pending", "to": "doing", "trigger": "巡检员点开任务并开始执行",
              "role": "u-inspector", "guard": "任务未被作废", "action": "记录开始时间"},
             {"id": "t-2", "from": "doing", "to": "done", "trigger": "巡检员点「标记完成」",
              "role": "u-inspector", "guard": "所有巡检项状态不为「待巡检」", "action": "记录完成时间"},
             {"id": "t-3", "from": "pending", "to": "void", "trigger": "质量主管确认删除任务",
              "role": "u-qm", "guard": "任务尚未开始执行", "action": "记录作废人与时间"},
             {"id": "t-4", "from": "doing", "to": "void", "trigger": "质量主管确认删除任务",
              "role": "u-qm", "guard": "已填写作废原因", "action": "记录作废人与原因"},
         ]},
    ],
    "capabilities": [
        {
            "id": "cap-inspect-start",
            "name": "开始巡检",
            "entity": "InspectTask",
            "actor": [
                "u-inspector"
            ],
            "from": [
                "pending"
            ],
            "guard": "任务未被作废",
            "policy": "disabled",
            "reason": "仅「待巡检」任务可以开始，当前不是该状态",
            "to": "doing",
            "effect": "记录开始时间",
            "page": "page-inspect-task",
            "requirement": "REQ-INSPECT-003"
        },
        {
            "id": "cap-inspect-done",
            "name": "标记完成",
            "entity": "InspectTask",
            "actor": [
                "u-inspector"
            ],
            "from": [
                "doing"
            ],
            "guard": "所有巡检项状态不为「待巡检」",
            "policy": "disabled",
            "reason": "仅「巡检中」任务可以完成，且所有巡检项需已填写",
            "to": "done",
            "effect": "记录完成时间并汇总异常项",
            "page": "page-inspect-task",
            "requirement": "REQ-INSPECT-003"
        },
        {
            "id": "cap-inspect-void",
            "name": "作废任务",
            "entity": "InspectTask",
            "actor": [
                "u-qm"
            ],
            "from": [
                "pending",
                "doing"
            ],
            "guard": "任务尚未完成",
            "policy": "hidden",
            "reason": "已完成的任务不可作废，如需处理请走异常流程",
            "to": "void",
            "effect": "记录作废人与原因",
            "page": "page-inspect-task",
            "requirement": "REQ-INSPECT-004"
        }
    ],
    "requirements": [
        {"id": "REQ-INSPECT-001", "pattern": "event-driven", "title": "选中主表行联动子表",
         "moduleId": "m-inspect", "pageId": "page-inspect-task", "role": "u-inspector",
         "trigger": "巡检员点击巡检任务主表中的某一行",
         "rule": "子表按所选行的任务编号过滤展示巡检项，且同一时刻只有一行处于选中态",
         "stateMachine": "", "expected": "子表在两帧内切换为该任务的巡检项，选中行加圆点与高亮底色",
         "acceptance": ["点击第 3 行后，子表内容与该行任务编号一致，且只有第 3 行高亮",
                        "点击已无明细的任务行时，子表区显示「该任务暂无巡检项」"],
         "priority": "P0", "source": "user", "status": "confirmed"},
        {"id": "REQ-INSPECT-002", "pattern": "event-driven", "title": "子表展开与收起",
         "moduleId": "m-inspect", "pageId": "page-inspect-task", "role": "u-inspector",
         "trigger": "巡检员点击子表标题栏",
         "rule": "子表在展开与收起之间切换，收起后主表占满可用高度",
         "stateMachine": "", "expected": "标题栏箭头方向与子表可见性同步变化",
         "acceptance": ["连续点击标题栏两次后回到初始可见性",
                        "收起状态下点击主表某行，子表自动展开"],
         "priority": "P1", "source": "user", "status": "confirmed"},
        {"id": "REQ-INSPECT-003", "pattern": "ubiquitous", "title": "任务状态与子表条数可见",
         "moduleId": "m-inspect", "pageId": "page-inspect-task", "role": "system",
         "trigger": "", "rule": "主表每行的状态标签与子表标题的明细条数始终可见",
         "stateMachine": "sm-inspect",
         "expected": "任务状态用统一色板表达；子表标题显示「共 N 条」",
         "acceptance": ["已作废任务在主表中显示为中性灰标签",
                        "选中行后子表标题条数等于该任务的巡检项条数"],
         "priority": "P1", "source": "demo", "status": "confirmed"},
        {"id": "REQ-INSPECT-004", "pattern": "unwanted", "title": "已作废任务禁止修改",
         "moduleId": "m-inspect", "pageId": "page-inspect-task", "role": "u-qm",
         "trigger": "质量主管对状态为已作废的任务点击操作列「修改」",
         "rule": "不打开修改抽屉，仅提示任务已作废",
         "stateMachine": "sm-inspect", "expected": "页面顶部出现提示「已作废的任务不可修改」",
         "acceptance": ["已作废任务点「修改」后抽屉保持关闭",
                        "非作废任务点「修改」正常打开抽屉",
                        "对已作废任务发起「标记完成」时被拒绝，任务状态保持已作废"],
         "priority": "P0", "source": "user", "status": "confirmed"},
        {"id": "REQ-INSPECT-005", "pattern": "option", "title": "主表分页",
         "moduleId": "m-inspect", "pageId": "page-inspect-task", "role": "u-inspector",
         "trigger": "", "rule": "主表按每页 10 条分页，并在底部显示总数与跳转入口",
         "stateMachine": "", "expected": "分页器当前页高亮，总数与筛选结果一致",
         "acceptance": ["切换页码后主表行数不超过 10",
                        "总数文案与筛选后的实际记录数一致"],
         "priority": "P1", "source": "demo", "status": "confirmed"},
        {"id": "REQ-INSPECT-006", "pattern": "event-driven", "title": "带参进入任务详情",
         "moduleId": "m-inspect", "pageId": "page-inspect-task-detail", "role": "u-inspector",
         "trigger": "巡检员在主表操作列点击「详情」",
         "rule": "跳转任务详情页并携带所选行的任务编号与任务名称",
         "stateMachine": "", "expected": "详情页展示的任务编号与名称与所点行一致，URL 含任务编号",
         "acceptance": ["点击第 2 行「详情」后详情页显示第 2 行的编号",
                        "直接打开带编号的详情地址时页面可正常渲染"],
         "priority": "P0", "source": "user", "status": "confirmed"},
    ],
    "boardPlan": [
        {"id": "bp-1", "order": 1, "name": "巡检任务管理（主子表）", "pageId": "page-inspect-task",
         "moduleId": "m-inspect", "status": "done",
         "reqIds": ["REQ-INSPECT-001", "REQ-INSPECT-002", "REQ-INSPECT-003",
                    "REQ-INSPECT-004", "REQ-INSPECT-005"]},
        {"id": "bp-2", "order": 2, "name": "巡检任务详情", "pageId": "page-inspect-task-detail",
         "moduleId": "m-inspect", "status": "doing", "reqIds": ["REQ-INSPECT-006"]},
    ],
    "glossary": [
        {"term": "巡检任务", "definition": "一次巡检计划落到某个车间/线体/物资上的执行单元，是主表的一行"},
        {"term": "巡检项", "definition": "任务下需要逐条执行并登记结果的最小检查单元，是子表的一行"},
        {"term": "主子表", "definition": "同一页面上下堆叠的两张表：主表选行、子表联动显示该行的明细"},
        {"term": "作废", "definition": "因停线等原因取消任务，作废后不可再修改，但可查看"},
        {"term": "频次维度", "definition": "巡检项的执行频率，由「数值 + 单位」组成，如 1 小时 / 2 班次"},
    ],
    "openQuestions": [
        {"id": "q-1", "question": "任务数很大时（3.6 万条），子表默认展开首行是否会拖慢首屏？"
                                  "是否需要提供「默认全部收起」开关",
         "owner": "PM", "status": "open", "answer": ""},
        {"id": "q-2", "question": "「已作废」目前复用「删除」入口（REQ-INSPECT-004 为推断），"
                                  "是否需要一个独立的「作废」按钮并填写原因",
         "owner": "AI", "status": "assumed",
         "answer": "暂按复用删除入口处理，待与质量主管确认后再决定是否拆出独立按钮"},
        {"id": "q-3", "question": "巡检项是否需要支持批量登记（勾选多项一次设为合格）",
         "owner": "PM", "status": "open", "answer": ""},
    ],
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
print("written:", OUT)
