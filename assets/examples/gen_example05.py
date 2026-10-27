#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 example-05-behavior-model.json —— 「行为建模 + 页面职责」全链路 few-shot。

场景：采购订单（PurchaseOrder）的全生命周期，刻意选一个与既有 4 个示例都不同的域，
用来证明「角色 × 状态 × 命令」这套建模方式与具体业务无关。

它演示四件事：
1. 一张单 6 个状态，每个按钮的可用性由 `capabilities[]` 决定，而不是写死 disabled；
2. 三个角色（采购员 / 采购主管 / 仓库）各自的任务拆到不同页面，靠状态机串起来；
3. 每个页面声明 `contract`（任务 / 角色 / 对象 / 负责的命令 / 提交边界）；
4. 详情页可切换「单据状态」，当场看到按钮置灰、隐藏、点了才拒绝三种策略的差别。

改数据请改本脚本再重跑，不要手改 JSON：
    python3 gen_example05.py
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genlib import finalize, dump

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "example-05-behavior-model.json")

STATUS_COLORS = {
    "草稿": "default", "待审批": "processing", "已审批": "success",
    "部分到货": "warning", "已关闭": "default", "已取消": "error",
}

# ---------------------------------------------------------------- 列表数据
ORDERS = [
    ("PO-20261018-0007", "草稿", "上海精工材料有限公司", "¥128,400.00", "张伟", "2026-10-25", "铝基板 300 张"),
    ("PO-20261018-0006", "待审批", "宁波恒信电子", "¥86,200.00", "张伟", "2026-10-24", "电容 12 万只"),
    ("PO-20261017-0005", "已审批", "苏州华瑞精密", "¥342,900.00", "李娜", "2026-10-22", "结构件 800 套"),
    ("PO-20261016-0004", "部分到货", "上海精工材料有限公司", "¥57,300.00", "李娜", "2026-10-20", "铜箔 40 卷"),
    ("PO-20261015-0003", "已关闭", "宁波恒信电子", "¥19,800.00", "张伟", "2026-10-18", "电阻 5 万只"),
    ("PO-20261014-0002", "已取消", "苏州华瑞精密", "¥73,500.00", "李娜", "2026-10-17", "外壳 200 套"),
]
ORDER_ROWS = [
    {"poNo": no, "status": st, "supplier": sp, "amount": am,
     "buyer": by, "expected": ex, "summary": sm}
    for (no, st, sp, am, by, ex, sm) in ORDERS
]

ITEMS = [
    ("MAT-10023", "铝基板 1.6mm", "300 张", "¥268.00", "¥80,400.00", "200"),
    ("MAT-10024", "铝基板 2.0mm", "120 张", "¥400.00", "¥48,000.00", "0"),
]
ITEM_ROWS = [
    {"mat": m, "spec": s, "qty": q, "price": p, "amount": a, "received": r}
    for (m, s, q, p, a, r) in ITEMS
]


def btn(nid, text, typ=None, cap=None, danger=False, extra=None):
    p = {"text": text}
    if typ:
        p["type"] = typ
    if danger:
        p["danger"] = True
    if cap:
        p["capability"] = cap
    if extra:
        p.update(extra)
    return {"id": nid, "type": "Button", "props": p}


# ---------------------------------------------------------------- 页面 1：列表
def page_list():
    return {
        "id": "page-po-list",
        "moduleId": "m-po",
        "name": "采购订单列表",
        "route": "/purchase/orders",
        "goal": "让采购员按状态与供应商找到目标订单，并就地完成提交审批或取消",
        "contract": {
            "task": "task-po-track",
            "actor": ["u-buyer"],
            "entity": "PurchaseOrder",
            "owns": ["cap-po-submit", "cap-po-cancel"],
            "submitBoundary": "none",
            "doneWhen": "目标订单已提交审批或被取消",
        },
        "layout": "header-content",
        "componentTree": {
            "id": "n-po-root", "type": "Layout", "props": {"layout": "header-content"},
            "children": [
                {"id": "n-po-header", "type": "Header",
                 "props": {"title": "采购订单", "back": False}},
                {"id": "n-po-content", "type": "Content", "children": [
                    {"id": "n-po-table", "type": "Table", "props": {
                        "title": "采购订单",
                        "size": "small",
                        "query": [
                            {"label": "采购单号", "type": "Input", "placeholder": "请输入采购单号"},
                            {"label": "状态", "type": "Select", "placeholder": "请选择",
                             "props": {"options": [{"value": k, "label": k} for k in STATUS_COLORS]}},
                            {"label": "供应商", "type": "Input", "placeholder": "请输入供应商名称"},
                        ],
                        "toolbar": [
                            {"type": "Button", "id": "n-btn-new",
                             "props": {"text": "新建订单", "type": "primary", "icon": "plus"}},
                            {"type": "Button", "id": "n-btn-export",
                             "props": {"text": "导出", "icon": "download"}},
                        ],
                        # XX-046：`total` 必须等于**真实行数**。P2a/P2b 把 total 当「数据量证据」
                        # 读（`_rows_gate`），写 1286 而只造 6 行，判据只能报
                        # `INCOMPLETE(INSUFFICIENT_ROWS)` —— 那是**教材自相矛盾**，不是判据太严。
                        # 也不能补造到 14 行：`ORDERS` 六条 status 两两不同、与 `STATUS_COLORS`
                        # 六键一一对应，补进来的只能是重复状态，等于改掉这份「行为模型」教材的用途。
                        # `pageSize` 跟着一起改：`pageSize 10 > total 6` 本身自相矛盾。
                        "pagination": {"total": len(ORDER_ROWS), "pageSize": len(ORDER_ROWS),
                                       "current": 1, "jump": True},
                        "columns": [
                            {"title": "采购单号", "dataIndex": "poNo", "width": 150},
                            {"title": "状态", "dataIndex": "status", "type": "tag"},
                            {"title": "供应商", "dataIndex": "supplier"},
                            {"title": "采购金额", "dataIndex": "amount", "align": "right"},
                            {"title": "采购员", "dataIndex": "buyer"},
                            {"title": "期望到货", "dataIndex": "expected"},
                            {"title": "操作", "dataIndex": "op", "type": "action", "width": 300,
                             "actions": [
                                 {"key": "detail", "label": "详情"},
                                 {"key": "approve", "label": "审批",
                                  "capability": "cap-po-approve"},
                                 {"key": "receive", "label": "收货",
                                  "capability": "cap-po-receive"},
                                 {"key": "submit", "label": "提交审批", "capability": "cap-po-submit"},
                                 {"key": "cancel", "label": "取消", "type": "danger",
                                  "capability": "cap-po-cancel"},
                             ]},
                        ],
                        "data": ORDER_ROWS,
                    }},
                    {"id": "n-modal-cancel", "type": "Modal", "props": {
                        "modalId": "m-cancel", "title": "取消采购订单",
                        "content": "取消后订单不可恢复。若已通知供应商，请同步告知对方。",
                        "okText": "确认取消", "cancelText": "再想想",
                    }},
                ]},
            ],
        },
        "states": [
            {"id": "s-default", "name": "默认态", "description": "默认：按创建时间倒序展示全部订单",
             "vars": {}, "overrides": []},
            {"id": "s-loading", "name": "加载态", "description": "加载中：表格骨架屏",
             "vars": {}, "overrides": [{"target": "n-po-table", "prop": "loading", "value": True}]},
            {"id": "s-empty", "name": "空态", "description": "空：筛选条件无匹配结果",
             "vars": {}, "overrides": [
                 {"target": "n-po-table", "prop": "data", "value": []},
                 {"target": "n-po-table", "prop": "emptyText", "value": "没有符合条件的采购订单，试试清空筛选"}]},
            {"id": "s-error", "name": "异常态", "description": "异常：采购服务不可用",
             "vars": {}, "overrides": [
                 {"target": "n-po-table", "prop": "data", "value": []},
                 {"target": "n-po-table", "prop": "emptyText", "value": "采购服务暂时不可用，请稍后重试（PO-503）"}]},
        ],
        "defaultStateId": "s-default",
        "interactions": [
            {"id": "ix-new", "name": "新建订单", "on": {"event": "click", "target": "n-btn-new"},
             "actions": [{"type": "navigate", "pageId": "page-po-create"}]},
            {"id": "ix-detail", "name": "查看订单详情（带参跳转）",
             "on": {"event": "click", "target": "n-po-table__act_*_detail"},
             "actions": [{"type": "navigate", "pageId": "page-po-detail",
                          "params": {"poNo": "{{row.poNo}}", "supplier": "{{row.supplier}}"}}]},
            {"id": "ix-submit", "name": "提交审批",
             "on": {"event": "click", "target": "n-po-table__act_*_submit"},
             "actions": [{"type": "message", "level": "success",
                          "text": "已提交审批，等待采购主管处理"}]},
            {"id": "ix-approve", "name": "进入审批页（改由状态驱动按钮可用性）",
             "on": {"event": "click", "target": "n-po-table__act_*_approve"},
             "actions": [{"type": "navigate", "pageId": "page-po-approve",
                          "params": {"poNo": "{{row.poNo}}", "supplier": "{{row.supplier}}"}}]},
            {"id": "ix-receive", "name": "进入收货页",
             "on": {"event": "click", "target": "n-po-table__act_*_receive"},
             "actions": [{"type": "navigate", "pageId": "page-po-receive",
                          "params": {"poNo": "{{row.poNo}}"}}]},
            {"id": "ix-cancel", "name": "取消订单（二次确认）",
             "on": {"event": "click", "target": "n-po-table__act_*_cancel"},
             "actions": [{"type": "showModal", "modalId": "m-cancel"}]},
            {"id": "ix-cancel-ok", "name": "确认取消订单",
             "on": {"event": "click", "target": "n-modal-cancel__ok"},
             "actions": [{"type": "hideModal", "modalId": "m-cancel"},
                         {"type": "message", "level": "success", "text": "订单已取消"}]},
        ],
        "annotations": [],
        "entryFrom": [],
        "exitTo": ["page-po-detail", "page-po-create"],
        "prd": {"reqIds": ["REQ-PO-001", "REQ-PO-006"], "sections": [
            {"id": "sec-list-1", "heading": "页面职责",
             "body": "采购员在这里完成两件事：**提交审批** 与 **取消订单**。\n"
                     "审批、到货登记属于其他角色，各自有独立页面 —— 本页只放「查看 / 提交 / 取消」三个动作，"
                     "避免把三个角色的任务揉进一屏。"},
            {"id": "sec-list-2", "heading": "状态与按钮",
             "body": "每一行的按钮可用性由该行自身的 `status` 决定，而不是整页统一：\n\n"
                     "- 草稿：可提交、可取消、可编辑（编辑在详情页）\n"
                     "- 待审批：可取消，提交置灰\n"
                     "- 已审批 / 部分到货：三个动作全部置灰，取消需要主管权限\n"
                     "- 已关闭 / 已取消：终态，仅可查看"},
        ]},
    }


# ---------------------------------------------------------------- 页面 2：详情
def page_detail():
    return {
        "id": "page-po-detail",
        "moduleId": "m-po",
        "parentId": "page-po-list",
        "name": "采购订单详情",
        "route": "/purchase/orders/:poNo",
        "entity": "PurchaseOrder",
        "stateMachine": "sm-po",
        "goal": "让采购员看清订单当前进度与明细，并执行本角色允许的动作",
        "contract": {
            "task": "task-po-track",
            "actor": ["u-buyer"],
            "entity": "PurchaseOrder",
            "owns": ["cap-po-edit", "cap-po-cancel-approved"],
            "submitBoundary": "none",
            "doneWhen": "订单信息已核对，或已完成修改 / 取消",
        },
        "layout": "header-content",
        "componentTree": {
            "id": "n-d-root", "type": "Layout", "props": {"layout": "header-content"},
            "children": [
                {"id": "n-d-header", "type": "Header", "props": {"title": "采购订单详情", "back": True}},
                {"id": "n-d-content", "type": "Content", "children": [
                    {"id": "n-d-title", "type": "Space", "props": {"size": 12, "align": "center"},
                     "children": [
                         {"id": "n-d-no", "type": "Typography",
                          "props": {"text": "{{poNo}}", "level": 4}},
                         {"id": "n-d-tag", "type": "Tag", "props": {"text": "{{__entState}}", "color": "default"}},
                         {"id": "n-d-tag-amt", "type": "Tag", "props": {"text": "¥128,400.00", "color": "purple"}},
                     ]},
                    {"id": "n-d-alert", "type": "Alert", "props": {
                        "type": "info", "showIcon": True,
                        "message": "本单当前为「{{__entState}}」",
                        "description": "可修改明细或提交审批；提交后进入审批流，不能再直接编辑。"}},
                    {"id": "n-d-desc", "type": "Descriptions", "props": {
                        "column": 3,
                        "items": [
                            {"label": "供应商", "value": "{{supplier}}"},
                            {"label": "采购员", "value": "张伟"},
                            {"label": "期望到货", "value": "2026-10-25"},
                            {"label": "收货仓库", "value": "华东中心仓"},
                            {"label": "结算方式", "value": "月结 30 天"},
                            {"label": "采购类型", "value": "常规采购"},
                        ]}},
                    {"id": "n-d-div1", "type": "Divider", "props": {"text": "采购明细"}},
                    {"id": "n-d-items", "type": "Table", "props": {
                        "size": "small",
                        "columns": [
                            {"title": "物料编码", "dataIndex": "mat", "width": 130},
                            {"title": "规格", "dataIndex": "spec"},
                            {"title": "订购数量", "dataIndex": "qty"},
                            {"title": "单价", "dataIndex": "price", "align": "right"},
                            {"title": "金额", "dataIndex": "amount", "align": "right"},
                            {"title": "已到货", "dataIndex": "received"},
                        ],
                        "data": ITEM_ROWS,
                        "emptyText": "本单还没有明细行",
                    }},
                    {"id": "n-d-div2", "type": "Divider", "props": {"text": "流转记录"}},
                    {"id": "n-d-timeline", "type": "Timeline", "props": {"items": [
                        {"text": "张伟 创建订单", "time": "2026-10-18 09:12"},
                        {"text": "等待提交审批", "time": "—"},
                    ]}},
                    {"id": "n-d-actions", "type": "Space", "props": {"size": 8}, "children": [
                        btn("n-d-btn-submit", "提交审批", "primary", "cap-po-submit"),
                        btn("n-d-btn-edit", "编辑订单", None, "cap-po-edit"),
                        btn("n-d-btn-cancel", "取消订单", None, "cap-po-cancel", danger=True),
                        btn("n-d-btn-void", "撤销审批", None, "cap-po-cancel-approved"),
                        btn("n-d-btn-print", "打印", None, "cap-po-print"),
                    ]},
                    {"id": "n-dr-edit", "type": "Drawer", "props": {
                        "modalId": "dr-edit", "title": "编辑采购订单", "width": 520,
                    }, "children": [
                        {"id": "n-dr-form", "type": "Form", "props": {"layout": "vertical"}, "children": [
                            {"id": "n-dr-fi1", "type": "FormItem", "props": {"label": "供应商", "required": True},
                             "children": [{"id": "n-dr-supplier", "type": "Select",
                                           "props": {"value": "上海精工材料有限公司",
                                                     "options": [{"value": "上海精工材料有限公司", "label": "上海精工材料有限公司"},
                                                                 {"value": "宁波恒信电子", "label": "宁波恒信电子"}]}}]},
                            {"id": "n-dr-fi2", "type": "FormItem", "props": {"label": "期望到货日期", "required": True},
                             "children": [{"id": "n-dr-date", "type": "DatePicker", "props": {"value": "2026-10-25"}}]},
                            {"id": "n-dr-fi3", "type": "FormItem", "props": {"label": "收货仓库", "required": True},
                             "children": [{"id": "n-dr-wh", "type": "Select",
                                           "props": {"value": "华东中心仓",
                                                     "options": [{"value": "华东中心仓", "label": "华东中心仓"},
                                                                 {"value": "华南中心仓", "label": "华南中心仓"}]}}]},
                            {"id": "n-dr-fi4", "type": "FormItem", "props": {"label": "备注"},
                             "children": [{"id": "n-dr-note", "type": "TextArea",
                                           "props": {"placeholder": "补充说明（选填）", "maxLength": 200}}]},
                        ]},
                        {"id": "n-dr-foot", "type": "Space", "props": {"size": 8}, "children": [
                            btn("n-btn-edit-cancel", "取消"),
                            btn("n-btn-edit-save", "保存", "primary"),
                        ]},
                    ]},
                ]},
            ],
        },
        "states": [
            {"id": "s-default", "name": "默认态", "description": "默认：展示订单信息、明细与流转记录",
             "vars": {"poNo": "PO-20261018-0007", "supplier": "上海精工材料有限公司"}, "overrides": []},
            {"id": "s-loading", "name": "加载态", "description": "加载中：信息区骨架屏",
             "vars": {}, "overrides": [{"target": "n-d-desc", "prop": "loading", "value": True}]},
            {"id": "s-error", "name": "异常态", "description": "异常：订单不存在或已被删除",
             "vars": {}, "overrides": [{"target": "n-d-timeline", "prop": "items", "value": []}]},
        ],
        "defaultStateId": "s-default",
        "notApplicableStates": ["empty"],
        "interactions": [
            {"id": "ix-d-submit", "name": "提交审批",
             "on": {"event": "click", "target": "n-d-btn-submit"},
             "actions": [{"type": "message", "level": "success", "text": "已提交审批，等待采购主管处理"}]},
            {"id": "ix-d-edit", "name": "打开编辑抽屉",
             "on": {"event": "click", "target": "n-d-btn-edit"},
             "actions": [{"type": "showDrawer", "drawerId": "dr-edit"}]},
            {"id": "ix-d-edit-cancel", "name": "关闭编辑抽屉",
             "on": {"event": "click", "target": "n-btn-edit-cancel"},
             "actions": [{"type": "hideDrawer", "drawerId": "dr-edit"}]},
            {"id": "ix-d-edit-save", "name": "保存修改",
             "on": {"event": "click", "target": "n-btn-edit-save"},
             "actions": [{"type": "hideDrawer", "drawerId": "dr-edit"},
                         {"type": "message", "level": "success", "text": "已保存"}]},
            {"id": "ix-d-cancel", "name": "取消已审批订单（点了才拒绝）",
             "on": {"event": "click", "target": "n-d-btn-cancel"},
             "actions": [{"type": "message", "level": "warning",
                          "text": "已审批订单取消需采购主管二次确认，已发起审批"}]},
            {"id": "ix-d-print", "name": "打印订单",
             "on": {"event": "click", "target": "n-d-btn-print"},
             "actions": [{"type": "message", "level": "info", "text": "已生成打印预览"}]},
        ],
        "annotations":         [
            {
                "id": "an-po-1",
                "pageId": "page-po-detail",
                "anchor": {
                    "nodeId": "n-d-btn-submit",
                    "x": 0.5,
                    "y": 0.5
                },
                "text": "「提交审批」在「待审批」及之后的状态下应置灰并说明原因，不要隐藏 —— 提交人需要看到「我确实提过了」，隐藏会让他以为操作没生效。",
                "category": "rule",
                "author": "PM",
                "status": "resolved",
                "createdAt": "2026-10-19T10:05:00+08:00",
                "replies": [
                    {
                        "author": "AI",
                        "text": "已改为 capability 驱动：n-d-btn-submit 绑定 cap-po-submit，from=[\"draft\"]、policy=\"disabled\"，悬停提示「仅草稿订单可以提交审批，当前状态：待审批」。",
                        "createdAt": "2026-10-19T10:12:00+08:00"
                    }
                ]
            },
            {
                "id": "an-po-2",
                "pageId": "page-po-detail",
                "anchor": {
                    "nodeId": "n-d-actions",
                    "x": 0.5,
                    "y": 0.5
                },
                "text": "操作区按钮顺序建议：主操作（提交 / 审批）在左，危险操作（取消订单）最右并加二次确认。",
                "category": "ui",
                "author": "PM",
                "status": "open",
                "createdAt": "2026-10-19T10:20:00+08:00"
            }
        ],
        "entryFrom": ["page-po-list"],
        "exitTo": [],
        "prd": {"reqIds": ["REQ-PO-004", "REQ-PO-006"], "sections": [
            {"id": "sec-d-1", "heading": "页面职责",
             "body": "本页只服务采购员的「跟踪 + 修改草稿」这一个任务。审批、到货登记都不在这里，"
                     "通过状态与角色跳转到各自页面 —— 详情页不再是「什么都能干」的万能页。"},
            {"id": "sec-d-2", "heading": "动作可用性（由 capabilities 决定）",
             "body": "| 动作 | 允许状态 | 不可用时 |\n|---|---|---|\n"
                     "| 提交审批 | 草稿 | 置灰，悬停提示仅草稿可提交 |\n"
                     "| 编辑订单 | 草稿 | **隐藏**（已提交不可编辑，避免误导）|\n"
                     "| 取消订单 | 草稿 / 待审批 | 置灰，提示当前状态不可取消 |\n"
                     "| 撤销审批 | 已审批 | 允许点击，二次确认后拒绝（`reject`）|\n"
                     "| 打印 | 不限 | 始终可用 |\n\n"
                     "用顶部「单据状态」下拉切换，可当场验证上述行为。"},
        ]},
    }


# ---------------------------------------------------------------- 页面 3：审批
def page_approve():
    return {
        "id": "page-po-approve",
        "moduleId": "m-po",
        "parentId": "page-po-list",
        "name": "采购订单审批",
        "route": "/purchase/orders/:poNo/approve",
        "entity": "PurchaseOrder",
        "stateMachine": "sm-po",
        "goal": "让采购主管在看清金额、供应商与明细后给出通过或驳回结论",
        "contract": {
            "task": "task-po-approve",
            "actor": ["u-manager"],
            "entity": "PurchaseOrder",
            "owns": ["cap-po-approve", "cap-po-reject"],
            "submitBoundary": "single",
            "doneWhen": "订单离开「待审批」，并留下审批人与意见",
        },
        "layout": "header-content",
        "componentTree": {
            "id": "n-ap-root", "type": "Layout", "props": {"layout": "header-content"},
            "children": [
                {"id": "n-ap-header", "type": "Header", "props": {"title": "采购订单审批", "back": True}},
                {"id": "n-ap-content", "type": "Content", "children": [
                    {"id": "n-ap-title", "type": "Space", "props": {"size": 12, "align": "center"},
                     "children": [
                         {"id": "n-ap-no", "type": "Typography", "props": {"text": "PO-20261018-0006", "level": 4}},
                         {"id": "n-ap-tag", "type": "Tag", "props": {"text": "{{__entState}}", "color": "processing"}},
                     ]},
                    {"id": "n-ap-alert", "type": "Alert", "props": {
                        "type": "warning", "showIcon": True,
                        "message": "该供应商近 90 天有 1 次延期交付",
                        "description": "建议核对交期后再决定；驳回会退回采购员修改，不进入审批记录。"}},
                    {"id": "n-ap-desc", "type": "Descriptions", "props": {
                        "column": 3,
                        "items": [
                            {"label": "供应商", "value": "宁波恒信电子"},
                            {"label": "采购金额", "value": "¥86,200.00"},
                            {"label": "采购员", "value": "张伟"},
                            {"label": "期望到货", "value": "2026-10-24"},
                            {"label": "收货仓库", "value": "华东中心仓"},
                            {"label": "明细行数", "value": "2 行"},
                        ]}},
                    {"id": "n-ap-form", "type": "Form", "props": {"layout": "vertical"}, "children": [
                        {"id": "n-ap-fi", "type": "FormItem",
                         "props": {"label": "审批意见", "required": True,
                                   "extra": "驳回时必填（5–200 字）；通过时可留空"},
                         "children": [{"id": "n-ap-note", "type": "TextArea",
                                       "props": {"placeholder": "写明判断依据，例如：单价高于上季度 8%，但交期可接受",
                                                 "maxLength": 200, "showCount": True}}]},
                    ]},
                    {"id": "n-ap-actions", "type": "Space", "props": {"size": 8}, "children": [
                        btn("n-ap-btn-approve", "通过", "primary", "cap-po-approve"),
                        btn("n-ap-btn-reject", "驳回", None, "cap-po-reject", danger=True),
                    ]},
                ]},
            ],
        },
        "states": [
            {"id": "s-default", "name": "默认态", "description": "默认：待审批，可给出结论",
             "vars": {}, "overrides": []},
            {"id": "s-loading", "name": "加载态", "description": "加载中：信息区骨架屏",
             "vars": {}, "overrides": [{"target": "n-ap-desc", "prop": "loading", "value": True}]},
            {"id": "s-error", "name": "异常态", "description": "异常：订单已被他人处理",
             "vars": {}, "overrides": [
                 {"target": "n-ap-alert", "prop": "type", "value": "error"},
                 {"target": "n-ap-alert", "prop": "message", "value": "该订单已被李娜审批（10:24），你的操作未生效"}]},
        ],
        "defaultStateId": "s-default",
        "notApplicableStates": ["empty"],
        "interactions": [
            {"id": "ix-ap-approve", "name": "审批通过",
             "on": {"event": "click", "target": "n-ap-btn-approve"},
             "actions": [{"type": "message", "level": "success", "text": "已通过，订单进入「已审批」"}]},
            {"id": "ix-ap-reject", "name": "驳回",
             "on": {"event": "click", "target": "n-ap-btn-reject"},
             "actions": [{"type": "message", "level": "warning", "text": "已驳回，订单退回采购员修改"}]},
        ],
        "annotations": [],
        "entryFrom": ["page-po-list", "page-po-detail"],
        "exitTo": [],
        "prd": {"reqIds": ["REQ-PO-002", "REQ-PO-005"], "sections": [
            {"id": "sec-ap-1", "heading": "为什么单独一页",
             "body": "审批是采购主管的任务，与采购员的任务不同角色、不同提交边界（审批意见是独立提交），"
                     "因此不塞进详情页。采购员在详情页看不到「通过 / 驳回」按钮 —— 功能权限在页面级就已隔离。"},
            {"id": "sec-ap-2", "heading": "并发冲突",
             "body": "两个主管同时打开同一张单是常态。异常态展示了「已被他人处理」的提示，"
                     "提交时以服务端状态为准，不做乐观覆盖。"},
        ]},
    }


# ---------------------------------------------------------------- 页面 4：到货登记
def page_receive():
    return {
        "id": "page-po-receive",
        "moduleId": "m-po",
        "parentId": "page-po-list",
        "name": "到货登记",
        "route": "/purchase/orders/:poNo/receive",
        "entity": "PurchaseOrder",
        "stateMachine": "sm-po",
        "goal": "让仓库管理员登记本次到货数量，并在全部到货后关闭订单",
        "contract": {
            "task": "task-po-receive",
            "actor": ["u-wh"],
            "entity": "PurchaseOrder",
            "owns": ["cap-po-receive", "cap-po-close"],
            "submitBoundary": "single",
            "doneWhen": "本次到货已入库，或订单已关闭",
        },
        "layout": "header-content",
        "componentTree": {
            "id": "n-rcv-root", "type": "Layout", "props": {"layout": "header-content"},
            "children": [
                {"id": "n-rcv-header", "type": "Header", "props": {"title": "到货登记", "back": True}},
                {"id": "n-rcv-content", "type": "Content", "children": [
                    {"id": "n-rcv-title", "type": "Space", "props": {"size": 12, "align": "center"},
                     "children": [
                         {"id": "n-rcv-no", "type": "Typography", "props": {"text": "PO-20261017-0005", "level": 4}},
                         {"id": "n-rcv-tag", "type": "Tag", "props": {"text": "{{__entState}}", "color": "success"}},
                     ]},
                    {"id": "n-rcv-desc", "type": "Descriptions", "props": {
                        "column": 3,
                        "items": [
                            {"label": "供应商", "value": "苏州华瑞精密"},
                            {"label": "收货仓库", "value": "华东中心仓"},
                            {"label": "期望到货", "value": "2026-10-22"},
                        ]}},
                    {"id": "n-rcv-items", "type": "Table", "props": {
                        "size": "small",
                        "columns": [
                            {"title": "物料编码", "dataIndex": "mat", "width": 130},
                            {"title": "规格", "dataIndex": "spec"},
                            {"title": "订购数量", "dataIndex": "qty"},
                            {"title": "已到货", "dataIndex": "received"},
                            {"title": "本次到货", "dataIndex": "thisTime"},
                        ],
                        "data": [dict(r, thisTime="") for r in ITEM_ROWS],
                        "emptyText": "本单没有待收货明细",
                    }},
                    {"id": "n-rcv-actions", "type": "Space", "props": {"size": 8}, "children": [
                        btn("n-rcv-btn-confirm", "确认本次到货", "primary", "cap-po-receive"),
                        btn("n-rcv-btn-close", "全部到货并关闭", None, "cap-po-close"),
                    ]},
                ]},
            ],
        },
        "states": [
            {"id": "s-default", "name": "默认态", "description": "默认：已审批订单，可登记到货",
             "vars": {}, "overrides": []},
            {"id": "s-loading", "name": "加载态", "description": "加载中：明细骨架屏",
             "vars": {}, "overrides": [{"target": "n-rcv-items", "prop": "loading", "value": True}]},
            {"id": "s-error", "name": "异常态", "description": "异常：明细拉取失败",
             "vars": {}, "overrides": [
                 {"target": "n-rcv-items", "prop": "data", "value": []},
                 {"target": "n-rcv-items", "prop": "emptyText", "value": "明细加载失败，请刷新重试（WMS-502）"}]},
        ],
        "defaultStateId": "s-default",
        "notApplicableStates": ["empty"],
        "interactions": [
            {"id": "ix-rcv-confirm", "name": "确认本次到货",
             "on": {"event": "click", "target": "n-rcv-btn-confirm"},
             "actions": [{"type": "message", "level": "success", "text": "到货已登记，订单状态更新为「部分到货」"}]},
            {"id": "ix-rcv-close", "name": "全部到货并关闭",
             "on": {"event": "click", "target": "n-rcv-btn-close"},
             "actions": [{"type": "message", "level": "success", "text": "订单已关闭"}]},
        ],
        "annotations": [],
        "entryFrom": ["page-po-list", "page-po-detail"],
        "exitTo": [],
        "prd": {"reqIds": ["REQ-PO-003"], "sections": [
            {"id": "sec-rcv-1", "heading": "独立页面的理由",
             "body": "仓库管理员的提交边界与采购员完全不同（到货数量是独立一次提交），"
                     "且到货可能分多次发生。放在详情页里会导致「保存」到底保存了什么说不清。"},
        ]},
    }


# ---------------------------------------------------------------- 页面 5：新建
def page_create():
    return {
        "id": "page-po-create",
        "moduleId": "m-po",
        "parentId": "page-po-list",
        "name": "新建采购订单",
        "route": "/purchase/orders/new",
        "entity": "PurchaseOrder",
        "stateMachine": "sm-po",
        "goal": "让采购员录入供应商、交期与明细，先存草稿再决定是否提交",
        "contract": {
            "task": "task-po-create",
            "actor": ["u-buyer"],
            "entity": "PurchaseOrder",
            "owns": ["cap-po-create"],
            "submitBoundary": "single",
            "doneWhen": "草稿已保存，或已直接提交审批",
        },
        "layout": "header-content",
        "componentTree": {
            "id": "n-new-root", "type": "Layout", "props": {"layout": "header-content"},
            "children": [
                {"id": "n-new-header", "type": "Header", "props": {"title": "新建采购订单", "back": True}},
                {"id": "n-new-content", "type": "Content", "children": [
                    {"id": "n-new-form", "type": "Form", "props": {"layout": "vertical"}, "children": [
                        {"id": "n-new-fi1", "type": "FormItem", "props": {"label": "供应商", "required": True},
                         "children": [{"id": "n-new-supplier", "type": "Select",
                                       "props": {"placeholder": "请选择供应商",
                                                 "options": [{"value": "s1", "label": "上海精工材料有限公司"},
                                                             {"value": "s2", "label": "宁波恒信电子"}]}}]},
                        {"id": "n-new-fi2", "type": "FormItem", "props": {"label": "采购类型", "required": True},
                         "children": [{"id": "n-new-type", "type": "RadioGroup",
                                       "props": {"value": "常规采购",
                                                 "options": ["常规采购", "紧急采购", "试样采购"]}}]},
                        {"id": "n-new-fi3", "type": "FormItem", "props": {"label": "期望到货日期", "required": True},
                         "children": [{"id": "n-new-date", "type": "DatePicker", "props": {"placeholder": "选择日期"}}]},
                        {"id": "n-new-fi4", "type": "FormItem", "props": {"label": "收货仓库", "required": True},
                         "children": [{"id": "n-new-wh", "type": "Select",
                                       "props": {"placeholder": "请选择仓库",
                                                 "options": [{"value": "w1", "label": "华东中心仓"},
                                                             {"value": "w2", "label": "华南中心仓"}]}}]},
                        {"id": "n-new-fi5", "type": "FormItem", "props": {"label": "结算方式"},
                         "children": [{"id": "n-new-pay", "type": "Select",
                                       "props": {"value": "月结 30 天",
                                                 "options": [{"value": "p1", "label": "月结 30 天"},
                                                             {"value": "p2", "label": "货到付款"}]}}]},
                        {"id": "n-new-fi6", "type": "FormItem", "props": {"label": "备注"},
                         "children": [{"id": "n-new-note", "type": "TextArea",
                                       "props": {"placeholder": "选填，200 字以内", "maxLength": 200}}]},
                    ]},
                    {"id": "n-new-tip", "type": "Alert", "props": {
                        "type": "info", "showIcon": True,
                        "message": "保存后为「草稿」，可继续编辑明细；提交后进入审批，不能再直接修改"}},
                    {"id": "n-new-actions", "type": "Space", "props": {"size": 8}, "children": [
                        btn("n-new-btn-save", "保存草稿", "primary", "cap-po-create"),
                        btn("n-new-btn-submit", "保存并提交审批", None, "cap-po-submit"),
                        btn("n-new-btn-cancel", "取消"),
                    ]},
                ]},
            ],
        },
        "states": [
            {"id": "s-default", "name": "默认态", "description": "默认：空表单，等待录入",
             "vars": {}, "overrides": []},
            {"id": "s-error", "name": "异常态", "description": "异常：供应商主数据加载失败",
             "vars": {}, "overrides": [
                 {"target": "n-new-supplier", "prop": "status", "value": "error"},
                 {"target": "n-new-supplier", "prop": "placeholder", "value": "供应商加载失败，请重试"}]},
        ],
        "defaultStateId": "s-default",
        "notApplicableStates": ["loading", "empty"],
        "interactions": [
            {"id": "ix-new-save", "name": "保存草稿",
             "on": {"event": "click", "target": "n-new-btn-save"},
             "actions": [{"type": "message", "level": "success", "text": "草稿已保存"},
                         {"type": "navigate", "pageId": "page-po-detail"}]},
            {"id": "ix-new-submit", "name": "保存并提交审批",
             "on": {"event": "click", "target": "n-new-btn-submit"},
             "actions": [{"type": "message", "level": "success", "text": "已提交审批"},
                         {"type": "navigate", "pageId": "page-po-list"}]},
            {"id": "ix-new-cancel", "name": "取消新建",
             "on": {"event": "click", "target": "n-new-btn-cancel"},
             "actions": [{"type": "back"}]},
        ],
        "annotations": [],
        "entryFrom": ["page-po-list"],
        "exitTo": ["page-po-detail", "page-po-list"],
        "prd": {"reqIds": ["REQ-PO-001"], "sections": [
            {"id": "sec-new-1", "heading": "新建与编辑分开",
             "body": "新建页只做「录入 + 保存/提交」；编辑在详情页用抽屉完成（草稿才可编辑）。"
                     "两者不共用同一个页面靠 mode 切换 —— 字段可编辑性、按钮、校验规则都不同，"
                     "混在一个页面最后会写成三层 if。"},
        ]},
    }


def main():
    data = {
        "meta": {
            "schemaVersion": "1.1",
            "product": "采购订单管理系统",
            "version": "0.1.0",
            "createdAt": "2026-10-19T09:30:00+08:00",
            "updatedAt": "2026-10-19T09:30:00+08:00",
            "reviewMode": False,
            "currentPageId": "page-po-list",
            "defaultPanel": "both",
        },
        "product": {
            "name": "采购订单管理系统",
            "oneLiner": "把采购申请、审批与到货登记串成一条可追踪的订单流。",
            "positioning": "面向制造业采购与仓储的中后台，解决「单子在哪一步、谁能动、动了之后去哪」三个问题。",
            "nonGoals": ["不做供应商寻源与比价", "不做财务付款与对账", "不做物流轨迹追踪"],
            "metrics": [
                {"name": "订单审批时长", "type": "duration", "target": "中位数 ≤ 4 小时"},
                {"name": "到货登记及时率", "type": "ratio", "target": "≥ 95%"},
            ],
        },
        "users": [
            {"id": "u-buyer", "name": "采购员", "description": "负责下单、跟踪交期、修改草稿",
             "goals": ["快速判断订单卡在哪一步", "减少与主管的口头确认"]},
            {"id": "u-manager", "name": "采购主管", "description": "负责审批订单金额与供应商选择",
             "goals": ["在有限信息下快速判断是否放行", "避免越权审批"]},
            {"id": "u-wh", "name": "仓库管理员", "description": "负责到货清点与入库登记",
             "goals": ["按单核对数量", "部分到货也能记录"]},
            {"id": "u-fin", "name": "财务", "description": "负责付款与对账（本示例不展开）",
             "goals": ["拿到可对账的订单与到货记录"]},
        ],
        "tasks": [
            {"id": "task-po-create", "name": "起草采购订单", "actor": "u-buyer",
             "goal": "把需求转成一张可提交的订单",
             "inputs": ["供应商", "物料与数量", "期望交期"],
             "doneWhen": "草稿已保存或已提交审批",
             "pages": ["page-po-create"]},
            {"id": "task-po-track", "name": "跟踪采购订单", "actor": "u-buyer",
             "goal": "确认订单当前处于哪一步，并完成本角色可执行的动作",
             "inputs": ["订单号", "状态", "流转记录"],
             "doneWhen": "订单已提交 / 已修改 / 已取消",
             "pages": ["page-po-list", "page-po-detail"]},
            {"id": "task-po-approve", "name": "审批采购订单", "actor": "u-manager",
             "goal": "判断金额与供应商是否可接受并给出结论",
             "inputs": ["金额", "供应商履约记录", "明细"],
             "doneWhen": "订单离开「待审批」并留下审批人",
             "pages": ["page-po-approve"]},
            {"id": "task-po-receive", "name": "登记到货", "actor": "u-wh",
             "goal": "按单核对本次到货数量并入库",
             "inputs": ["订单明细", "实收数量"],
             "doneWhen": "本次到货已登记，或订单已关闭",
             "pages": ["page-po-receive"]},
        ],
        "userFlows": [
            {"id": "flow-po", "name": "采购订单主流程", "role": "u-buyer",
             "goal": "从下单到关闭的全过程",
             "steps": [
                 {"id": "fs-1", "name": "新建订单", "pageId": "page-po-create", "note": "保存草稿"},
                 {"id": "fs-2", "name": "提交审批", "pageId": "page-po-detail", "note": "草稿 → 待审批"},
                 {"id": "fs-3", "name": "主管审批", "pageId": "page-po-approve", "note": "通过 / 驳回"},
                 {"id": "fs-4", "name": "仓库登记到货", "pageId": "page-po-receive", "note": "可多次"},
                 {"id": "fs-5", "name": "关闭订单", "pageId": "page-po-receive", "note": "全部到货"},
             ]},
        ],
        "modules": [
            {"id": "m-po", "name": "采购管理", "priority": "P0",
             "goal": "覆盖采购订单的创建、审批与到货",
             "pageIds": ["page-po-list", "page-po-detail", "page-po-create",
                         "page-po-approve", "page-po-receive"]},
        ],
        "pages": [page_list(), page_detail(), page_approve(), page_receive(), page_create()],
        "components": [
            {"id": "c-table", "name": "采购订单表格", "antd": "Table",
             "spec": "列表页主表，支持查询条、操作条、分页；行内动作受状态约束",
             "variants": [{"name": "带查询条"}, {"name": "只读明细"}],
             "states": ["默认", "加载", "空", "异常"]},
            {"id": "c-desc", "name": "订单信息区", "antd": "Descriptions",
             "spec": "三列展示订单主信息，窄屏降为两列",
             "variants": [{"name": "三列"}, {"name": "两列"}],
             "states": ["默认", "加载"]},
            {"id": "c-btn", "name": "命令按钮", "antd": "Button",
             "spec": "可用性由 capabilities 决定，不在组件上写死 disabled",
             "variants": [{"name": "主要"}, {"name": "次要"}, {"name": "危险"}],
             "states": ["默认", "悬停", "加载", "置灰", "隐藏"]},
        ],
        "stateMachines": [
            {"id": "sm-po", "name": "采购订单状态机", "entity": "PurchaseOrder", "initial": "draft",
             "states": [
                 {"id": "draft", "name": "草稿", "type": "normal"},
                 {"id": "pending", "name": "待审批", "type": "warning"},
                 {"id": "approved", "name": "已审批", "type": "success"},
                 {"id": "partially_received", "name": "部分到货", "type": "warning"},
                 {"id": "closed", "name": "已关闭", "type": "disabled"},
                 {"id": "cancelled", "name": "已取消", "type": "error"},
             ],
             # 每条转移都带 `ui`：指明它由哪个页面的哪个交互触发（XX-019）。
             # 这条链是状态机 → 页面按钮的唯一定位方式，缺了它就只剩「流程想清楚了」，
             # 证明不了「页面上点得出来」。系统自动流转写 {"kind": "system"}。
             "transitions": [
                 {"id": "t-po-1", "from": "draft", "to": "pending",
                  "trigger": "采购员点击「提交审批」", "role": "u-buyer",
                  "guard": "供应商、交期、至少一条明细均已填写", "action": "锁定订单字段并通知主管",
                  "ui": {"pageId": "page-po-list", "interactionId": "ix-submit"}},
                 {"id": "t-po-2", "from": "pending", "to": "approved",
                  "trigger": "主管点击「通过」", "role": "u-manager",
                  "guard": "审批意见可留空", "action": "记录审批人与时间",
                  "ui": {"pageId": "page-po-approve", "interactionId": "ix-ap-approve"}},
                 {"id": "t-po-3", "from": "pending", "to": "draft",
                  "trigger": "主管点击「驳回」", "role": "u-manager",
                  "guard": "审批意见 5–200 字", "action": "记录驳回意见并通知采购员",
                  "ui": {"pageId": "page-po-approve", "interactionId": "ix-ap-reject"}},
                 {"id": "t-po-4", "from": "approved", "to": "partially_received",
                  "trigger": "仓库管理员点击「确认本次到货」", "role": "u-wh",
                  "guard": "本次到货数量大于 0 且不超过未到货数量", "action": "写入入库单",
                  "ui": {"pageId": "page-po-receive", "interactionId": "ix-rcv-confirm"}},
                 {"id": "t-po-5", "from": "partially_received", "to": "closed",
                  "trigger": "仓库管理员点击「全部到货并关闭」", "role": "u-wh",
                  "guard": "所有明细已到货", "action": "关闭订单并通知采购员",
                  "ui": {"pageId": "page-po-receive", "interactionId": "ix-rcv-close"}},
                 {"id": "t-po-6", "from": "draft", "to": "cancelled",
                  "trigger": "采购员点击「取消」", "role": "u-buyer",
                  "guard": "订单仍为草稿", "action": "记录取消原因",
                  "ui": {"pageId": "page-po-list", "interactionId": "ix-cancel-ok"}},
                 {"id": "t-po-7", "from": "pending", "to": "cancelled",
                  "trigger": "采购员点击「取消」", "role": "u-buyer",
                  "guard": "主管尚未处理", "action": "撤回审批并通知主管",
                  "ui": {"pageId": "page-po-list", "interactionId": "ix-cancel-ok"}},
                 {"id": "t-po-8", "from": "approved", "to": "cancelled",
                  "trigger": "主管点击「取消已审批订单」", "role": "u-manager",
                  "guard": "未发生任何到货", "action": "释放供应商产能并记录原因",
                  "ui": {"pageId": "page-po-detail", "interactionId": "ix-d-cancel"}},
                 {"id": "t-po-9", "from": "approved", "to": "closed",
                  "trigger": "超过 30 天未登记到货", "role": "system", "system": True,
                  "guard": "无入库记录", "action": "自动关闭并通知采购员",
                  "ui": {"kind": "system"}},
             ]},
        ],
        "capabilities": [
            {"id": "cap-po-create", "name": "保存草稿", "entity": "PurchaseOrder",
             "actor": ["u-buyer"], "from": [], "policy": "disabled",
             "effect": "生成草稿订单并进入详情", "page": "page-po-create",
             "requirement": "REQ-PO-001"},
            {"id": "cap-po-submit", "name": "提交审批", "entity": "PurchaseOrder",
             "actor": ["u-buyer"], "from": ["draft"],
             "guard": "供应商、交期、至少一条明细均已填写", "policy": "disabled",
             "reason": "仅「草稿」订单可以提交审批，当前为「待审批 / 已审批 / 已关闭」",
             "to": "pending", "effect": "锁定订单字段并通知采购主管", "page": "page-po-list",
             "requirement": "REQ-PO-001", "onFail": "明细为空时提示先添加物料"},
            {"id": "cap-po-edit", "name": "编辑订单", "entity": "PurchaseOrder",
             "actor": ["u-buyer"], "from": ["draft"],
             "guard": "订单仍为草稿", "policy": "hidden",
             "reason": "已提交的订单不可直接编辑，如需变更请撤回后重提",
             "effect": "打开编辑抽屉", "page": "page-po-detail", "requirement": "REQ-PO-004"},
            {"id": "cap-po-cancel", "name": "取消订单", "entity": "PurchaseOrder",
             "actor": ["u-buyer"], "from": ["draft", "pending"],
             "guard": "主管尚未处理", "policy": "disabled",
             "reason": "仅「草稿 / 待审批」订单可以取消，已审批订单需主管操作",
             "to": "cancelled", "effect": "记录取消原因并通知相关人", "page": "page-po-list",
             "requirement": "REQ-PO-006", "onFail": "已审批时提示联系采购主管"},
            {"id": "cap-po-approve", "name": "通过", "entity": "PurchaseOrder",
             "actor": ["u-manager"], "from": ["pending"],
             "guard": "当前用户为采购主管且非下单人", "policy": "disabled",
             "reason": "仅「待审批」订单可以审批，当前不是该状态",
             "to": "approved", "effect": "记录审批人与时间并通知采购员", "page": "page-po-approve",
             "requirement": "REQ-PO-002", "onFail": "订单已被他人处理时提示刷新"},
            {"id": "cap-po-reject", "name": "驳回", "entity": "PurchaseOrder",
             "actor": ["u-manager"], "from": ["pending"],
             "guard": "审批意见 5–200 字", "policy": "disabled",
             "reason": "仅「待审批」订单可以驳回，当前不是该状态",
             "to": "draft", "effect": "退回采购员修改并记录意见", "page": "page-po-approve",
             "requirement": "REQ-PO-002", "onFail": "意见过短时在输入框下提示"},
            {"id": "cap-po-receive", "name": "确认本次到货", "entity": "PurchaseOrder",
             "actor": ["u-wh"], "from": ["approved", "partially_received"],
             "guard": "本次到货数量大于 0 且不超过未到货数量", "policy": "disabled",
             "reason": "仅「已审批 / 部分到货」订单可以登记到货",
             "to": "partially_received", "effect": "写入入库单并更新已到货数量",
             "page": "page-po-receive", "requirement": "REQ-PO-003",
             "onFail": "数量超出时提示核对实物"},
            {"id": "cap-po-close", "name": "全部到货并关闭", "entity": "PurchaseOrder",
             "actor": ["u-wh"], "from": ["partially_received"],
             "guard": "所有明细已到货", "policy": "disabled",
             "reason": "仅「部分到货」订单可以关闭，且所有明细需已到齐",
             "to": "closed", "effect": "关闭订单并通知采购员", "page": "page-po-receive",
             "requirement": "REQ-PO-003", "onFail": "未到齐时提示剩余数量"},
            {"id": "cap-po-cancel-approved", "name": "取消已审批订单", "entity": "PurchaseOrder",
             "actor": ["u-manager"], "from": ["approved"],
             "guard": "未发生任何到货", "policy": "reject",
             "reason": "已审批订单取消需主管二次确认，且必须尚未到货",
             "to": "cancelled", "effect": "释放供应商产能并记录原因", "page": "page-po-detail",
             "requirement": "REQ-PO-005", "onFail": "已有到货时提示走退货流程"},
            {"id": "cap-po-print", "name": "打印订单", "entity": "PurchaseOrder",
             "actor": ["u-buyer", "u-manager"], "from": [], "policy": "disabled",
             "effect": "生成打印预览", "page": "page-po-detail", "requirement": "REQ-PO-006"},
        ],
        # 每条需求都声明 `ui`（XX-020），三选一，与 transitions[].ui 同构：
        #   {"interactionId": "ix-xxx"}  由某个交互触发
        #   {"kind": "system"}           系统自动（这里没有，但 schema 支持）
        #   {"kind": "page-enter"}       进页面即满足，不需要点击（约束类需求）
        "requirements": [
            {"id": "REQ-PO-001", "pageId": "page-po-create", "moduleId": "m-po",
             "ui": {"interactionId": "ix-new-submit"},
             "title": "提交采购订单审批", "pattern": "event-driven",
             "trigger": "采购员在草稿订单上点击「提交审批」",
             "rule": "订单必须已填供应商、期望到货日期与至少一条明细",
             "expected": "订单状态由「草稿」变为「待审批」，字段锁定并通知采购主管",
             "stateMachine": "sm-po", "role": "u-buyer", "status": "confirmed", "source": "user",
             "acceptance": [
                 "草稿订单点击「提交审批」后状态变为「待审批」，编辑入口消失",
                 "明细为空时提交被拒绝，提示「请先添加至少一条物料」",
                 "非草稿状态下「提交审批」按钮置灰，点击时提示当前状态不允许",
             ]},
            {"id": "REQ-PO-002", "pageId": "page-po-approve", "moduleId": "m-po",
             "ui": {"interactionId": "ix-ap-approve"},
             "title": "采购主管审批订单", "pattern": "event-driven",
             "trigger": "采购主管在待审批订单上点击「通过」或「驳回」",
             "rule": "仅待审批订单可审批；驳回必须填写 5–200 字意见",
             "expected": "通过则状态变为「已审批」；驳回则退回「草稿」并记录意见",
             "stateMachine": "sm-po", "role": "u-manager", "status": "confirmed", "source": "user",
             "acceptance": [
                 "通过后订单进入「已审批」，采购员收到通知",
                 "驳回意见少于 5 字时提交被拒绝，输入框下方提示字数要求",
                 "订单已被他人审批时提示「该订单已被处理」，不做覆盖",
             ]},
            {"id": "REQ-PO-003", "pageId": "page-po-receive", "moduleId": "m-po",
             "ui": {"interactionId": "ix-rcv-confirm"},
             "title": "仓库登记到货", "pattern": "event-driven",
             "trigger": "仓库管理员点击「确认本次到货」或「全部到货并关闭」",
             "rule": "本次到货数量需大于 0 且不超过未到货数量；关闭需所有明细到齐",
             "expected": "登记后已到货数量累加，状态变为「部分到货」；到齐后关闭订单",
             "stateMachine": "sm-po", "role": "u-wh", "status": "confirmed", "source": "user",
             "acceptance": [
                 "登记 200 张后订单状态变为「部分到货」，已到货数量更新为 200",
                 "本次到货数量超过未到货数量时被拒绝，提示剩余可收数量",
                 "未到齐时点击「全部到货并关闭」被拒绝，提示还差多少",
             ]},
            {"id": "REQ-PO-004", "pageId": "page-po-detail", "moduleId": "m-po",
             "ui": {"kind": "page-enter"},
             "title": "已提交订单不可编辑", "pattern": "unwanted",
             "trigger": "",
             "rule": "订单离开「草稿」后不允许直接编辑，只能查看或走撤回",
             "expected": "编辑入口在非草稿状态下不出现，接口层同样拒绝编辑请求",
             "stateMachine": "sm-po", "role": "u-buyer", "status": "confirmed", "source": "user",
             "acceptance": [
                 "待审批及之后状态下详情页没有「编辑订单」按钮（入口直接隐藏）",
                 "直接调用编辑接口返回 409 并拒绝修改，提示先撤回",
             ]},
            {"id": "REQ-PO-005", "pageId": "page-po-approve", "moduleId": "m-po",
             # 与 REQ-PO-002 共用同一个交互：两个需求可以绑同一处点击，
             # 校验器只判「指得准」，不判「一对一」（那会把「越权被拒」逼成假接口）。
             "ui": {"interactionId": "ix-ap-approve"},
             "title": "越权审批被拒绝", "pattern": "unwanted",
             "trigger": "",
             "rule": "只有采购主管可以审批，且不能审批自己下的单",
             "expected": "非主管看不到审批入口；下单人审批时被拒绝并提示原因",
             "stateMachine": "sm-po", "role": "u-manager", "status": "confirmed", "source": "user",
             "acceptance": [
                 "采购员访问审批页时按钮置灰并提示需要「采购主管」角色",
                 "下单人点击通过时被拒绝，提示「不能审批自己创建的订单」",
             ]},
            {"id": "REQ-PO-006", "pageId": "page-po-detail", "moduleId": "m-po",
             "ui": {"kind": "page-enter"},
             "title": "动作可用性随状态变化", "pattern": "state-driven",
             "trigger": "",
             "rule": "每个动作的可用状态由命令策略决定，不可用时需说明原因",
             "expected": "切换单据状态时，按钮按策略置灰 / 隐藏 / 点击后拒绝",
             "stateMachine": "sm-po", "role": "u-buyer", "status": "confirmed", "source": "user",
             "acceptance": [
                 "草稿态可提交、可编辑；待审批态提交置灰且编辑隐藏",
                 "置灰按钮点击时提示当前状态与允许状态，不是无反应",
                 "终态（已关闭 / 已取消）下不出现任何可逆动作",
             ]},
        ],
        "boardPlan": [],
        "glossary": [
            {"term": "草稿", "definition": "已创建但未提交审批的订单，可自由修改"},
            {"term": "部分到货", "definition": "已有入库记录但明细尚未全部到齐"},
            {"term": "命令策略", "definition": "描述「谁在什么状态下能执行什么动作」的规则集合，capabilities[] 的每一项"},
        ],
        "openQuestions": [
            {"id": "q-po-1", "question": "已审批订单取消是否需要财务同步确认？",
             "status": "open", "answer": "暂定只需主管二次确认，待财务确认后调整"},
        ],
        "dataModel": {
            "entities": [
                {"id": "e-po", "name": "PurchaseOrder", "table": "purchase_order",
                 "description": "采购订单主表",
                 "pageIds": ["page-po-list", "page-po-detail", "page-po-approve",
                             "page-po-receive", "page-po-create"],
                 "fields": [
                     {"name": "id", "type": "bigint", "key": "pk"},
                     {"name": "poNo", "type": "varchar(32)", "required": True, "unique": True,
                      "constraint": "PO-YYYYMMDD-NNNN"},
                     {"name": "status", "type": "varchar(24)", "required": True,
                      "constraint": "draft|pending|approved|partially_received|closed|cancelled"},
                     {"name": "supplierId", "type": "bigint", "required": True},
                     {"name": "amount", "type": "decimal(14,2)", "required": True},
                     {"name": "buyerId", "type": "bigint", "required": True},
                     {"name": "expectedDate", "type": "date", "required": True},
                     {"name": "warehouseId", "type": "bigint", "required": True},
                     {"name": "settlement", "type": "varchar(32)"},
                     {"name": "approvedBy", "type": "bigint"},
                     {"name": "approvedAt", "type": "datetime"},
                     {"name": "cancelReason", "type": "varchar(200)"},
                 ],
                 "relations": [
                     {"type": "has_many", "target": "e-po-item", "via": "poId"},
                     {"type": "belongs_to", "target": "e-supplier", "via": "supplierId"},
                 ],
                 "indexes": ["uk_po_no", "idx_status_created"]},
                {"id": "e-po-item", "name": "PurchaseOrderItem", "table": "purchase_order_item",
                 "description": "采购订单明细行",
                 "fields": [
                     {"name": "id", "type": "bigint", "key": "pk"},
                     {"name": "poId", "type": "bigint", "required": True},
                     {"name": "materialCode", "type": "varchar(32)", "required": True},
                     {"name": "spec", "type": "varchar(120)"},
                     {"name": "qty", "type": "decimal(12,3)", "required": True},
                     {"name": "price", "type": "decimal(12,4)", "required": True},
                     {"name": "receivedQty", "type": "decimal(12,3)", "required": True,
                      "constraint": "0 <= receivedQty <= qty"},
                 ]},
                {"id": "e-supplier", "name": "Supplier", "table": "supplier",
                 "description": "供应商主数据",
                 "fields": [
                     {"name": "id", "type": "bigint", "key": "pk"},
                     {"name": "name", "type": "varchar(120)", "required": True, "unique": True},
                     {"name": "contact", "type": "varchar(40)"},
                     {"name": "leadTimeDays", "type": "int"},
                     {"name": "lateDeliveries", "type": "int", "note": "近 90 天延期次数"},
                 ]},
            ],
            "derived": [
                {"name": "unreceivedQty", "expr": "qty - receivedQty",
                 "fallback": "0", "usedBy": ["page-po-receive"], "reqId": "REQ-PO-003"},
            ],
        },
    }
    finalize(data, "example-05")
    dump(data, OUT)


if __name__ == "__main__":
    main()
