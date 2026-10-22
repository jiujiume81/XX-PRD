#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 example-06-dense-list.json —— 「作业型列表页」范本（I-07 §7.1）。

为什么这个示例比规范文字更重要：
  在它之前，5 个示例里 `Table` 只在「顺带有个表格」的地方出现，而且都是 middle 档、
  列宽不声明、没有抽屉、统计卡横在表格上面。模型据此学到的「合格长相」就是那个样子 ——
  于是「先建模再画页面」写多少遍都压不过教材。示例权重高于规范文字，这条已在 I-01 定过。

这个示例要让人学到 5 件事（对应 §7.1）：
1. **筛选区两行三列**：6 字段全常显，label 76 右对齐，控件 32 高 / 295 宽，动作独立一行；
   `收起` 只折第 4–6 个字段（`.fb-field.more`）。
2. **8 列怎么排**：验收档 866 放 8 列，Σwidth = 866，`tableLayout:'fixed'`；
   1026 档是**同一套 8 列**在不同内容宽下的表现（列集在生成时定、Σ 恒等于 866，运行时不切列）。
3. **行高**：`size:'xs'`，设计值 32 / 实测 34；评审态一屏 **9 折算行（8 整行，1440 档）/ 12 折算行（11 整行，1600 档）**，
   产品态 18 行。超长文本走按列 `ellipsis` + `title`，不撑行高。
4. **抽屉详情**：`rowClick → showDrawer`（不是 navigate），抽屉 560 宽，内含 6 列子表。
5. **空态与零结果的差别**：`s-empty` 给「去建检验任务」，`s-no-result` 给「清空筛选」。

刻意不用：`Statistic`（统计迁到独立页 page-iqc-stats）、`MasterDetail`（列表页形态不是它）。

改数据请改本脚本再重跑，不要手改 JSON：
    python3 gen_example06.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "example-06-dense-list.json")

STATUS_COLORS = {
    "待检验": "warning",
    "检验中": "processing",
    "待判定": "purple",
    "已关闭": "default",
    "不合格": "error",
}

# 验收档 866 的列宽预算（I-07 §3.9，替代方案 §3.5 规则 3）。
#
# 为什么必须重排：`.xs` 定在 14px（§3.1 的裁定），而原预算
# （48/152/148/120/88/150/84/76）是按 13px 的文本宽算的。14px 下主键三列装不下：
#   任务单号  实测文本 161，原声明 152 → 列内 128 → 裁字（且没配 ellipsis）
#   批次号    实测文本 120，原声明 120 → 列内  96 → 裁字
#   操作      实测文本  61，原声明  76 → 列内  52 → 裁字
# 「接受 14px」不是一句同意，它连带这次重排 —— 这行的账必须一起结（§3.1「代价」）。
#
# 序号 48 是 P17 的硬下限（每列 ≥48），不是「44 加 4」：44 放不下两位序号 + 左右 padding。
# 三条不变量（允许 ±2 微调，但必须同时成立）：
#   ① Σ = 866；② 主键三列（任务单号/批次号/操作）不裁字；③ ellipsis 恰 2 列且都真溢出。
# 866 档不设固定列（fix）：本来就不横向滚动，sticky 列只会多一层 z-index 噪音。
COLUMNS = [
    {"title": "序号", "dataIndex": "no", "width": 48, "align": "left"},
    {"title": "任务单号", "dataIndex": "taskNo", "width": 188},
    {"title": "物资名称", "dataIndex": "material", "width": 125, "ellipsis": True},
    {"title": "批次号", "dataIndex": "lot", "width": 146},
    {"title": "取样·样品", "dataIndex": "samples", "width": 88, "align": "right"},
    {"title": "质检标准", "dataIndex": "standard", "width": 103, "ellipsis": True},
    {"title": "状态", "dataIndex": "status", "width": 80, "type": "tag"},
    {"title": "操作", "dataIndex": "op", "width": 88, "type": "action",
     "actions": [
         {"key": "detail", "label": "详情"},
         {"key": "start", "label": "开始", "capability": "cap-iqc-start"},
     ]},
]
assert sum(c["width"] for c in COLUMNS) == 866, sum(c["width"] for c in COLUMNS)
assert [c["title"] for c in COLUMNS if c.get("ellipsis")] == ["物资名称", "质检标准"], \
    "ellipsis 只能留在两列长文本上（§3.9）"

# ---------------------------------------------------------------- 列表数据（≥20 行）
# 物资名称与质检标准都要**真的**超列宽：P18 判「配了 ellipsis 的列必须真溢出」，
# 配了却不溢出的省略号是装饰，会让真正该截断的列混在里面看不出来。
RAW = [
    ("IQC-20261022-0020", "三元正极材料 NCM811", "LOT-A26-1022", "12/3", "YS/T 798-2012 镍钴锰酸锂", "待检验"),
    ("IQC-20261022-0019", "磷酸铁锂 LFP-200", "LOT-B14-1022", "8/2", "GB/T 24533-2019 石墨类负极", "检验中"),
    ("IQC-20261022-0018", "超细球形钴酸锂 D50 12μm", "LOT-C08-1022", "6/2", "GB/T 26008-2020 电池用电解液", "待判定"),
    ("IQC-20261022-0017", "导电炭黑 Super-P", "LOT-D31-1022", "4/1", "HG/T 3072-2019 炭黑吸碘值", "待检验"),
    ("IQC-20261022-0016", "聚偏氟乙烯 PVDF 5130", "LOT-E02-1022", "5/1", "GB/T 32684-2016 胶粘剂", "已关闭"),
    ("IQC-20261022-0015", "铝箔 12μm 双面光", "LOT-F19-1022", "10/2", "GB/T 36146-2018 锂电铝箔", "已关闭"),
    ("IQC-20261022-0014", "铜箔 6μm 高抗拉", "LOT-G05-1022", "10/2", "GB/T 5230-2020 电解铜箔", "检验中"),
    ("IQC-20261021-0013", "N-甲基吡咯烷酮 NMP", "LOT-H22-1021", "3/1", "GB/T 27563-2011 工业用 NMP", "已关闭"),
    ("IQC-20261021-0012", "隔膜 16μm 陶瓷涂覆", "LOT-J11-1021", "8/2", "GB/T 36363-2018 锂电隔膜", "待判定"),
    ("IQC-20261021-0011", "六氟磷酸锂 LiPF6", "LOT-K07-1021", "4/1", "GB/T 19282-2014 六氟磷酸锂", "待检验"),
    ("IQC-20261021-0010", "石墨负极 S360 人造", "LOT-L30-1021", "9/2", "GB/T 24533-2019 石墨类负极", "已关闭"),
    ("IQC-20261021-0009", "羧甲基纤维素钠 CMC", "LOT-M16-1021", "3/1", "GB 1886.232-2016 食品添加剂", "不合格"),
    ("IQC-20261020-0008", "丁苯橡胶 SBR 乳液", "LOT-N09-1020", "5/1", "GB/T 8658-2020 丁苯胶乳", "已关闭"),
    ("IQC-20261020-0007", "铝塑膜 113μm 银灰", "LOT-P24-1020", "6/1", "QB/T 5500-2020 铝塑复合膜", "已关闭"),
    ("IQC-20261020-0006", "三元正极材料 NCM622", "LOT-Q13-1020", "12/3", "YS/T 798-2012 镍钴锰酸锂", "检验中"),
    ("IQC-20261020-0005", "磷酸铁锂 LFP-300 高倍率", "LOT-R28-1020", "10/2", "GB/T 33827-2017 磷酸铁锂", "待检验"),
    ("IQC-20261019-0004", "导电石墨 KS-6", "LOT-S04-1019", "4/1", "GB/T 3519-2008 微晶石墨", "已关闭"),
    ("IQC-20261019-0003", "电解液 LB-347 高电压", "LOT-T18-1019", "4/1", "GB/T 26008-2020 电池用电解液", "已关闭"),
    ("IQC-20261019-0002", "粘结剂 PVDF  HSV900", "LOT-U21-1019", "5/1", "GB/T 32684-2016 胶粘剂", "待判定"),
    ("IQC-20261019-0001", "镍钴铝酸锂 NCA 92%", "LOT-V06-1019", "12/3", "YS/T 1125-2016 镍钴铝酸锂", "已关闭"),
]


def rows():
    out = []
    for i, (no, mat, lot, smp, std, st) in enumerate(RAW, start=1):
        out.append({
            "no": str(i), "taskNo": no, "material": mat, "lot": lot,
            "samples": smp, "standard": std, "status": st, "op": "",
        })
    return out


# 超长文本态：不是「造两条超长数据」，而是把真实字段放大到明显溢出，
# 用来验证「ellipsis + title 不撑行高」（P9 与 P18 同时在这一态上看得最清楚）。
LONG_ROWS = rows()
LONG_ROWS[0]["material"] = "超细球形三元正极材料 NCM811（单晶，D50 10–12μm，比表 0.25m²/g）"
LONG_ROWS[0]["standard"] = "YS/T 798-2012 镍钴锰酸锂（含 2021 年第 2 号修改单，附录 B 粒度与比表方法）"
LONG_ROWS[1]["material"] = "磷酸铁锂 LFP-200（碳包覆，压实密度 2.55g/cm³，克容量 155mAh/g）"
LONG_ROWS[1]["standard"] = "GB/T 24533-2019 锂离子电池石墨类负极材料（附录 C 首次库伦效率测定）"


def btn(nid, text, typ=None, cap=None, icon=None, extra=None):
    p = {"text": text}
    if typ:
        p["type"] = typ
    if cap:
        p["capability"] = cap
    if icon:
        p["icon"] = icon
    if extra:
        p.update(extra)
    return {"id": nid, "type": "Button", "props": p}


def seg(nid, options, value):
    return {"id": nid, "type": "Segmented", "props": {"options": options, "value": value}}


# ---------------------------------------------------------------- 页面 1：列表
def page_list():
    table_props = {
        # 密度与形态
        "size": "xs",
        "tableLayout": "fixed",
        "stickyHeader": True,
        # 高度预算：`calc(100vh - 438px)`。438 不是「余量」，是两项之和：
        #     表格顶 392（实测：页头 56 + 内容 padding 24 + 标题带 40 + gap 16
        #                  + 筛选区 144 + gap 16 + 表头 34 + …）
        #   + 分页脚 46（.ant-table-foot 的 padding 12+4 与 30 高的 .pg 控件）
        #   = 438。
        # 为什么是 438 而不是需求单写的 428：428 假定分页脚 36 高，实测 46
        # （30 的 .pg + 上下 padding 16）。按 428 写，1600 档分页底 867 > 视口 857 ——
        # P16「分页在首屏内」直接红。按 438 写，两档分页底恰好 857/757 = 视口底
        # （bottom ≤ vh，0 余量），行数 1600: 419/34=12、1440: 319/34=9 —— 没有为好看牺牲密度。
        # 不写成 maxHeight:'none'：那样表格会长到把分页顶出首屏（P16 红）。
        "maxHeight": "calc(100vh - 438px)",
        "stickyFooter": True,
        # 筛选区：两行三列
        "filterBar": "grid3",
        "query": [
            {"label": "任务单号", "type": "Input", "placeholder": "如 IQC-20261022-0019"},
            {"label": "请验日期", "type": "DatePicker", "placeholder": "开始日期"},
            {"label": "状态", "type": "Select",
             "props": {"options": [{"value": s, "label": s} for s in
                                   ["待检验", "检验中", "待判定", "已关闭", "不合格"]]}},
            {"label": "物资名称", "type": "Input", "placeholder": "支持模糊匹配"},
            {"label": "批次号", "type": "Input", "placeholder": "如 LOT-A26"},
            {"label": "检验类型", "type": "Select",
             "props": {"options": [{"value": "来料检验", "label": "来料检验"},
                                   {"value": "复检", "label": "复检"},
                                   {"value": "免检抽验", "label": "免检抽验"}]}},
        ],
        "queryId": "n-btn-query",
        "resetId": "n-btn-reset",
        # 分页：342 条 → 18 页。pageSize 10 会变成 35 页，翻页成本 ×2
        "pagination": {"total": 342, "pageSize": 20, "current": 1, "jump": False},
        "columns": COLUMNS,
        "data": rows(),
        "rowKey": "taskNo",
        "rowClick": True,
        "emptyAction": {"text": "去建检验任务", "type": "primary", "icon": "plus",
                        "id": "n-btn-empty-new"},
    }

    tree = {
        "id": "n-iqc-root", "type": "Layout", "props": {"layout": "header-sider-content"},
        "children": [
            {"id": "n-iqc-sider", "type": "Sider", "props": {"width": 208, "title": "质量中心"},
             "children": [
                 {"id": "n-iqc-menu", "type": "Menu", "props": {
                     "mode": "inline", "selectedKey": "iqc",
                     "items": [
                         {"key": "iqc", "label": "来料检验", "icon": "check"},
                         {"key": "ipqc", "label": "过程检验", "icon": "activity"},
                         {"key": "oqc", "label": "出货检验", "icon": "send"},
                         {"key": "ncr", "label": "不合格品", "icon": "alert"},
                         {"key": "stats", "label": "检验统计", "icon": "chart"},
                     ]}},
             ]},
            {"id": "n-iqc-header", "type": "Header", "props": {"title": "来料检验"}},
            {"id": "n-iqc-content", "type": "Content", "children": [
                # 标题带：h1 + 计数筛选 + 主操作，同一行。三者都**不**各自成行 ——
                # 「提示条 / 主操作行 / 工具条」各自占一行是表格被推到 476px 的直接原因。
                {"id": "n-iqc-title", "type": "Space",
                 "props": {"align": "center", "size": 12, "justify": "space-between", "block": True},
                 "children": [
                     {"id": "n-iqc-title-l", "type": "Space", "props": {"align": "center", "size": 12},
                      "children": [
                          {"id": "n-iqc-h1", "type": "Typography",
                           "props": {"level": 1, "text": "来料检验任务"}},
                          seg("n-iqc-seg", ["全部 342", "待检验 18", "检验中 6", "待判定 3"], "全部 342"),
                      ]},
                     {"id": "n-iqc-title-r", "type": "Space", "props": {"align": "center", "size": 8},
                      "children": [
                          btn("n-btn-stats", "检验统计", icon="chart"),
                          # 导出必须绑 capability：不绑的话校验器给 INFO「建了命令但界面上看不到」，
                          # 而这条命令恰恰是本页 owns 的（contract.owns 里有 cap-iqc-export）。
                          btn("n-btn-export", "导出", cap="cap-iqc-export", icon="download"),
                          btn("n-btn-new", "新建检验任务", typ="primary", cap="cap-iqc-create", icon="plus"),
                      ]},
                 ]},
                {"id": "n-iqc-table", "type": "Table", "props": table_props},
                # 抽屉详情：列表页只留一条主路径（看 → 抽屉），不跳页。
                # 跳页会把「我现在在看哪一行」这件事从屏幕上抹掉，回来还得重新找。
                {"id": "n-iqc-drawer", "type": "Drawer", "props": {
                    "title": "检验任务详情 · IQC-20261022-0020", "width": 560, "placement": "right"},
                 "children": [
                     {"id": "n-dw-desc", "type": "Descriptions", "props": {
                         "column": 2, "size": "small",
                         "items": [
                             {"label": "任务单号", "value": "IQC-20261022-0020"},
                             {"label": "状态", "value": "待检验"},
                             {"label": "物资名称", "value": "三元正极材料 NCM811"},
                             {"label": "批次号", "value": "LOT-A26-1022"},
                             {"label": "请验数量", "value": "3,000 kg"},
                             {"label": "取样数量", "value": "12 件 / 3 件"},
                             {"label": "质检标准", "value": "YS/T 798-2012 镍钴锰酸锂"},
                             {"label": "供应商", "value": "青海锂业新材料"},
                         ]}},
                     {"id": "n-dw-table-title", "type": "Typography",
                      "props": {"text": "检验项目（6 项）"}},
                     {"id": "n-dw-table", "type": "Table", "props": {
                         "size": "small", "tableLayout": "fixed",
                         "columns": [
                             {"title": "项目", "dataIndex": "item", "width": 96},
                             {"title": "方法", "dataIndex": "method", "width": 96},
                             {"title": "标准值", "dataIndex": "spec", "width": 96, "align": "right"},
                             {"title": "实测", "dataIndex": "value", "width": 72, "align": "right"},
                             {"title": "结论", "dataIndex": "result", "width": 64, "type": "tag"},
                         ],
                         "data": [
                             {"item": "镍含量", "method": "滴定", "spec": "≥ 88.0%", "value": "88.6%", "result": "合格"},
                             {"item": "水分", "method": "卡尔费休", "spec": "≤ 500ppm", "value": "312ppm", "result": "合格"},
                             {"item": "D50 粒度", "method": "激光粒度", "spec": "10–12μm", "value": "11.2μm", "result": "合格"},
                             {"item": "比表面积", "method": "BET", "spec": "0.20–0.35", "value": "0.27", "result": "合格"},
                             {"item": "磁性异物", "method": "磁棒吸附", "spec": "≤ 20ppb", "value": "14ppb", "result": "合格"},
                             {"item": "pH 值", "method": "电位法", "spec": "10.5–11.5", "value": "11.8", "result": "不合格"},
                         ]}},
                     {"id": "n-dw-actions", "type": "Space", "props": {"align": "center", "size": 8},
                      "children": [
                          btn("n-dw-close", "关闭"),
                          # 抽屉底部三件套对应状态机里三条人工转移：
                          #   检验中 → 待判定（提交结果）/ 待判定 → 已关闭（判定合格）
                          #   / 待判定 → 检验中（需复检）。
                          # 只在行内放「开始」的示例，读者学到的是一条半截流程。
                          btn("n-dw-start", "开始检验", typ="primary", cap="cap-iqc-start"),
                          btn("n-dw-submit", "提交检验结果", typ="primary", cap="cap-iqc-submit"),
                          btn("n-dw-approve", "判定合格", typ="primary", cap="cap-iqc-approve"),
                          btn("n-dw-recheck", "需复检", cap="cap-iqc-recheck"),
                      ]},
                 ]},
            ]},
        ],
    }

    return {
        "id": "page-iqc-list",
        "moduleId": "m-iqc",
        "name": "来料检验任务",
        "route": "/iqc/tasks",
        "goal": "让检验员按批次与状态找到待检任务，就地打开详情并开始检验",
        "contract": {
            "task": "task-iqc-track",
            "actor": ["u-inspector"],
            "entity": "InspectionTask",
            # 本页 owns 四条命令：开始 / 导出 / 提交结果 / 判定合格 / 需复检。
            # 「判定」归质量工程师，但落点是本页的抽屉 —— 命令的主页面按**承载交互的页面**算，
            # 不按角色算（同一命令只能有一个主页面，否则校验器报「被两页同时声明」）。
            "owns": ["cap-iqc-start", "cap-iqc-export", "cap-iqc-submit",
                     "cap-iqc-approve", "cap-iqc-recheck"],
            "submitBoundary": "none",
            "doneWhen": "目标任务已打开详情或已开始检验",
        },
        "layout": "header-sider-content",
        "componentTree": tree,
        "states": [
            {"id": "s-default", "name": "默认态",
             "description": "默认：按请验时间倒序展示全部 342 条中的第 1 页（20 行）",
             "vars": {}, "overrides": []},
            {"id": "s-loading", "name": "加载态",
             "description": "加载中：表格骨架屏，筛选区与标题带保持可见",
             "vars": {}, "overrides": [{"target": "n-iqc-table", "prop": "loading", "value": True}]},
            {"id": "s-empty", "name": "空态",
             "description": "空：本月还没有建过检验任务 —— 给「去建检验任务」",
             "vars": {},
             "overrides": [
                 {"target": "n-iqc-table", "prop": "data", "value": []},
                 {"target": "n-iqc-table", "prop": "emptyText", "value": "本月还没有来料检验任务"},
                 {"target": "n-iqc-table", "prop": "emptyAction",
                  "value": {"text": "去建检验任务", "type": "primary", "icon": "plus",
                            "id": "n-btn-empty-new"}},
             ]},
            {"id": "s-no-result", "name": "零结果态",
             "description": "零结果：筛选后 0 条 —— 文案与动作都不同于全空",
             "vars": {},
             "overrides": [
                 {"target": "n-iqc-table", "prop": "data", "value": []},
                 {"target": "n-iqc-table", "prop": "emptyText", "value": "没有符合条件的检验任务，试试清空筛选"},
                 {"target": "n-iqc-table", "prop": "emptyAction",
                  "value": {"text": "清空筛选", "id": "n-btn-empty-reset"}},
             ]},
            {"id": "s-error", "name": "异常态",
             "description": "异常：检验服务不可用",
             "vars": {},
             "overrides": [
                 {"target": "n-iqc-table", "prop": "data", "value": []},
                 {"target": "n-iqc-table", "prop": "emptyText", "value": "检验服务暂时不可用，请稍后重试（IQC-503）"},
             ]},
            {"id": "s-long-text", "name": "超长文本态",
             "description": "超长文本：物资名称与标准名远超列宽，验证 ellipsis + title 不撑行高",
             "vars": {},
             "overrides": [{"target": "n-iqc-table", "prop": "data", "value": LONG_ROWS}]},
        ],
        "defaultStateId": "s-default",
        "interactions": [
            {"id": "ix-row-detail", "name": "点行打开详情抽屉",
             "on": {"event": "click", "target": "n-iqc-table__row_*"},
             "actions": [{"type": "showDrawer", "drawerId": "n-iqc-drawer"}]},
            {"id": "ix-drawer-close", "name": "关闭详情抽屉",
             "on": {"event": "click", "target": "n-dw-close"},
             "actions": [{"type": "hideDrawer", "drawerId": "n-iqc-drawer"}]},
            {"id": "ix-start", "name": "开始检验",
             "on": {"event": "click", "target": "n-iqc-table__act_*_start"},
             "actions": [{"type": "message", "level": "success", "text": "已开始检验，状态变为「检验中」"}]},
            # 抽屉里的三条人工转移各有一个按钮 —— 状态机里写「谁点的」，这里写「点哪个」。
            # 少了这一段，「待判定 → 已关闭」在页面上就没有落点（QMS 那 11 个 ERROR 的成因）。
            {"id": "ix-submit", "name": "提交检验结果",
             "on": {"event": "click", "target": "n-dw-submit"},
             "actions": [{"type": "message", "level": "success", "text": "结果已提交，状态变为「待判定」"},
                         {"type": "hideDrawer", "drawerId": "n-iqc-drawer"}]},
            {"id": "ix-approve", "name": "判定合格并关闭",
             "on": {"event": "click", "target": "n-dw-approve"},
             "actions": [{"type": "message", "level": "success", "text": "已判定合格，批次放行，任务关闭"},
                         {"type": "hideDrawer", "drawerId": "n-iqc-drawer"}]},
            {"id": "ix-recheck", "name": "判定需复检",
             "on": {"event": "click", "target": "n-dw-recheck"},
             "actions": [{"type": "message", "level": "warning", "text": "已生成复检任务，状态回到「检验中」"},
                         {"type": "hideDrawer", "drawerId": "n-iqc-drawer"}]},
            {"id": "ix-new", "name": "新建检验任务",
             "on": {"event": "click", "target": "n-btn-new"},
             "actions": [{"type": "navigate", "pageId": "page-iqc-new"}]},
            {"id": "ix-stats", "name": "看检验统计",
             "on": {"event": "click", "target": "n-btn-stats"},
             "actions": [{"type": "navigate", "pageId": "page-iqc-stats"}]},
            {"id": "ix-export", "name": "导出当前筛选结果",
             "on": {"event": "click", "target": "n-btn-export"},
             "actions": [{"type": "message", "level": "info", "text": "已导出 342 条（按当前筛选）"}]},
            {"id": "ix-query", "name": "按条件查询",
             "on": {"event": "click", "target": "n-btn-query"},
             "actions": [{"type": "message", "level": "info", "text": "已按条件筛选"}]},
            {"id": "ix-reset", "name": "重置筛选",
             "on": {"event": "click", "target": "n-btn-reset"},
             "actions": [{"type": "message", "level": "info", "text": "筛选条件已清空"}]},
        ],
        "annotations": [],
        "entryFrom": [],
        "exitTo": ["page-iqc-new", "page-iqc-stats"],
        "prd": {"reqIds": ["REQ-IQC-002", "REQ-IQC-003"], "sections": [
            {"id": "sec-iqc-1", "heading": "页面职责",
             "body": "检验员在这里完成三件事：**找到任务**、**看一眼详情**、**开始检验**。\n"
                     "判定与关闭属于质量工程师（在详情抽屉里完成），新建是独立页面 —— 本页不承担它们。"},
            {"id": "sec-iqc-2", "heading": "为什么详情是抽屉不是跳页",
             "body": "跳页会把「我在看第几行」从屏幕上抹掉，回来要重新找一遍。\n"
                     "抽屉宽 560，866 档下还剩 306px 能看到当前行 —— **详情不许占用列表高度**，"
                     "这是「一屏多 13 行」与「一屏 6 行」的差别所在。"},
            {"id": "sec-iqc-3", "heading": "为什么没有统计卡",
             "body": "统计卡占 272px，正好是 8 行数据。要看数量用标题带的 `Segmented`（不额外占行），"
                     "要看趋势去 `检验统计` 页 —— 那里没有数据行要抢高度。"},
        ]},
    }


# ---------------------------------------------------------------- 页面 2：新建
def page_new():
    return {
        "id": "page-iqc-new",
        "moduleId": "m-iqc",
        "name": "新建检验任务",
        "route": "/iqc/tasks/new",
        "goal": "把一张请验单转成可执行的检验任务",
        "contract": {
            "task": "task-iqc-create",
            "actor": ["u-inspector"],
            "entity": "InspectionTask",
            "owns": ["cap-iqc-create"],
            # 一页一次提交（表单页）。原写 "page" 不在 single/staged/none 里 ——
            # 枚举里没有 "page"，那是把「提交边界是页面」这句人话直接写进了字段。
            # 不要改成 "none"：本页确实有提交边界（保存即产生一张单据）。
            "submitBoundary": "single",
            "doneWhen": "任务已保存为待检验",
        },
        "layout": "header-sider-content",
        "componentTree": {
            "id": "n-new-root", "type": "Layout", "props": {"layout": "header-sider-content"},
            "children": [
                {"id": "n-new-sider", "type": "Sider", "props": {"width": 208, "title": "质量中心"},
                 "children": [{"id": "n-new-menu", "type": "Menu", "props": {
                     "mode": "inline", "selectedKey": "iqc",
                     "items": [{"key": "iqc", "label": "来料检验", "icon": "check"}]}}]},
                {"id": "n-new-header", "type": "Header", "props": {"title": "新建检验任务", "back": True}},
                {"id": "n-new-content", "type": "Content", "children": [
                    # 错误提示只在异常态出现：默认态用 state.hidden 收起来。
                    # 表单页也要有加载/空/异常三态 —— 「这一页只会正常」是原型里最常见的谎。
                    {"id": "n-new-alert", "type": "Alert", "props": {
                        "type": "error", "text": "请验单查询失败（SRV-502），请重试或手工录入"}},
                    {"id": "n-new-form", "type": "Form", "props": {"layout": "vertical"}, "children": [
                        {"id": "n-new-fi1", "type": "FormItem", "props": {"label": "物资", "required": True},
                         "children": [{"id": "n-new-material", "type": "Select", "props": {
                             "options": [{"value": "NCM811", "label": "三元正极材料 NCM811"},
                                         {"value": "LFP200", "label": "磷酸铁锂 LFP-200"}]}}]},
                        {"id": "n-new-fi2", "type": "FormItem", "props": {"label": "批次号", "required": True},
                         "children": [{"id": "n-new-lot", "type": "Input", "props": {"placeholder": "如 LOT-A26-1022"}}]},
                        {"id": "n-new-fi3", "type": "FormItem", "props": {"label": "请验数量", "required": True},
                         "children": [{"id": "n-new-qty", "type": "InputNumber", "props": {"placeholder": "kg"}}]},
                        {"id": "n-new-fi4", "type": "FormItem", "props": {"label": "检验类型"},
                         "children": [{"id": "n-new-kind", "type": "RadioGroup", "props": {
                             "options": [{"value": "full", "label": "全检"},
                                         {"value": "sample", "label": "抽检"}]}}]},
                        {"id": "n-new-fi5", "type": "FormItem", "props": {"label": "备注"},
                         "children": [{"id": "n-new-note", "type": "TextArea", "props": {"placeholder": "选填"}}]},
                    ]},
                    {"id": "n-new-actions", "type": "Space", "props": {"align": "center", "size": 8},
                     "children": [
                         btn("n-new-cancel", "取消"),
                         btn("n-new-save", "保存为待检验", typ="primary", cap="cap-iqc-create"),
                     ]},
                ]},
            ],
        },
        "states": [
            {"id": "s-default", "name": "默认态", "description": "新建表单", "vars": {},
             "overrides": [], "hidden": ["n-new-alert"]},
            {"id": "s-loading", "name": "加载态",
             "description": "加载中：从请验单跳转进来，正在回填物资与批次号",
             "vars": {}, "hidden": ["n-new-alert"],
             "overrides": [{"target": "n-new-save", "prop": "loading", "value": True}]},
            {"id": "s-empty", "name": "空态",
             "description": "空：从菜单直接进入，没有请验单可转 —— 表单为空，保存置灰",
             "vars": {}, "hidden": ["n-new-alert"],
             "overrides": [{"target": "n-new-material", "prop": "placeholder", "value": "请选择物资"},
                           {"target": "n-new-save", "prop": "disabled", "value": True}]},
            {"id": "s-error", "name": "异常态",
             "description": "异常：请验单查询失败（SRV-502），可重试或手工录入",
             "vars": {},
             "overrides": [{"target": "n-new-alert", "prop": "text",
                            "value": "请验单查询失败（SRV-502），请重试或手工录入"}]},
        ],
        "defaultStateId": "s-default",
        "interactions": [
            {"id": "ix-save", "name": "保存草稿",
             "on": {"event": "click", "target": "n-new-save"},
             "actions": [{"type": "message", "level": "success", "text": "已创建，状态：待检验"},
                         {"type": "navigate", "pageId": "page-iqc-list"}]},
            {"id": "ix-cancel", "name": "取消并返回",
             "on": {"event": "click", "target": "n-new-cancel"},
             "actions": [{"type": "navigate", "pageId": "page-iqc-list"}]},
        ],
        "annotations": [],
        "entryFrom": ["page-iqc-list"],
        "exitTo": ["page-iqc-list"],
        "prd": {"reqIds": ["REQ-IQC-001"], "sections": [
            {"id": "sec-new-1", "heading": "页面职责",
             "body": "只做一件事：把请验单转成待检验任务。检验结果不在这里填。"},
        ]},
    }


# ---------------------------------------------------------------- 页面 3：统计
def page_stats():
    return {
        "id": "page-iqc-stats",
        "moduleId": "m-iqc",
        "name": "检验统计",
        "route": "/iqc/stats",
        "goal": "看趋势与分布，回答「这个月质量在变好还是变坏」",
        "contract": {
            "task": "task-iqc-stats",
            "actor": ["u-engineer"],
            "entity": "InspectionTask",
            "owns": ["cap-iqc-stats-export"],
            "submitBoundary": "none",
            "doneWhen": "已看清趋势并可按指标下钻",
        },
        "layout": "header-sider-content",
        "componentTree": {
            "id": "n-st-root", "type": "Layout", "props": {"layout": "header-sider-content"},
            "children": [
                {"id": "n-st-sider", "type": "Sider", "props": {"width": 208, "title": "质量中心"},
                 "children": [{"id": "n-st-menu", "type": "Menu", "props": {
                     "mode": "inline", "selectedKey": "stats",
                     "items": [{"key": "iqc", "label": "来料检验"}, {"key": "stats", "label": "检验统计"}]}}]},
                {"id": "n-st-header", "type": "Header", "props": {"title": "检验统计"}},
                {"id": "n-st-content", "type": "Content", "children": [
                    {"id": "n-st-title", "type": "Space",
                     "props": {"align": "center", "size": 12, "justify": "space-between", "block": True},
                     "children": [
                         {"id": "n-st-title-l", "type": "Space", "props": {"align": "center", "size": 12},
                          "children": [
                              {"id": "n-st-h1", "type": "Typography", "props": {"level": 1, "text": "检验统计"}},
                              seg("n-st-seg", ["本周", "本月", "本季"], "本月"),
                          ]},
                         {"id": "n-st-title-r", "type": "Space", "props": {"align": "center", "size": 8},
                          "children": [
                              # 统计页也要 owns ≥1 条命令：没有导出/下钻的看板是只读图片，
                              # 而「只读看板」这个结构今天还不存在（§5.3，见 §4 第 11 条）。
                              btn("n-btn-stats-export", "导出报表", cap="cap-iqc-stats-export", icon="download"),
                          ]},
                     ]},
                    {"id": "n-st-alert", "type": "Alert", "props": {
                        "type": "error", "text": "统计服务暂时不可用（STA-503），请稍后重试"}},
                    # 统计页才允许四张指标卡：这里没有数据行要抢高度
                    {"id": "n-st-row", "type": "Row", "props": {"gutter": 16}, "children": [
                        {"id": "n-st-c1", "type": "Col", "props": {"span": 6}, "children": [
                            {"id": "n-st-s1", "type": "Statistic", "props": {"title": "在检批次", "value": "18"}}]},
                        {"id": "n-st-c2", "type": "Col", "props": {"span": 6}, "children": [
                            {"id": "n-st-s2", "type": "Statistic", "props": {"title": "待判定", "value": "3"}}]},
                        {"id": "n-st-c3", "type": "Col", "props": {"span": 6}, "children": [
                            {"id": "n-st-s3", "type": "Statistic", "props": {"title": "超期未完成", "value": "2"}}]},
                        {"id": "n-st-c4", "type": "Col", "props": {"span": 6}, "children": [
                            {"id": "n-st-s4", "type": "Statistic", "props": {"title": "不合格率", "value": "1.8%"}}]},
                    ]},
                    {"id": "n-st-chart1", "type": "Chart", "props": {
                        "title": "近 12 周来料量与不合格率", "height": 320,
                        "data": [{"label": "W31", "value": 62}, {"label": "W32", "value": 58},
                                 {"label": "W33", "value": 71}, {"label": "W34", "value": 66},
                                 {"label": "W35", "value": 78}, {"label": "W36", "value": 74},
                                 {"label": "W37", "value": 69}, {"label": "W38", "value": 81},
                                 {"label": "W39", "value": 77}, {"label": "W40", "value": 83},
                                 {"label": "W41", "value": 79}, {"label": "W42", "value": 72}]}},
                    # 主图 + 次图：主图 320 回答「趋势」，次图 280 回答「不合格都出在哪」。
                    # 一张图回答两个问题 = 两张图都读不清（§5.3）。
                    {"id": "n-st-chart2", "type": "Chart", "props": {
                        "title": "不合格原因分布（本月）", "height": 280,
                        "data": [{"label": "磁性异物", "value": 12}, {"label": "水分超标", "value": 9},
                                 {"label": "粒度超差", "value": 7}, {"label": "比表异常", "value": 4},
                                 {"label": "其它", "value": 3}]}},
                ]},
            ],
        },
        "states": [
            {"id": "s-default", "name": "默认态", "description": "本月统计", "vars": {},
             "overrides": [], "hidden": ["n-st-alert"]},
            {"id": "s-loading", "name": "加载态",
             "description": "加载中：图表骨架，指标行保留上次值并置灰",
             "vars": {}, "hidden": ["n-st-alert"],
             "overrides": [{"target": "n-st-chart1", "prop": "loading", "value": True}]},
            {"id": "s-empty", "name": "空态",
             "description": "空：本月还没有检验数据 —— 图表区给「本月无数据」，不是画一条 0 线",
             "vars": {}, "hidden": ["n-st-alert"],
             "overrides": [{"target": "n-st-chart1", "prop": "data", "value": []},
                           {"target": "n-st-chart2", "prop": "data", "value": []}]},
            {"id": "s-error", "name": "异常态",
             "description": "异常：统计服务不可用（STA-503），可重试",
             "vars": {},
             "overrides": [{"target": "n-st-alert", "prop": "text",
                            "value": "统计服务暂时不可用（STA-503），请稍后重试"}]},
        ],
        "defaultStateId": "s-default",
        "interactions": [
            {"id": "ix-st-back", "name": "回到列表",
             "on": {"event": "click", "target": "n-st-seg"},
             "actions": [{"type": "navigate", "pageId": "page-iqc-list"}]},
            # 四张指标卡各可下钻：统计的价值在「看到异常 → 立刻看到是哪些单」，
            # 只给数字不给下钻，等于把结论和责任都留给读者（§5.3 / D11）。
            {"id": "ix-drill-inspecting", "name": "下钻：在检批次",
             "on": {"event": "click", "target": "n-st-s1"},
             "actions": [{"type": "navigate", "pageId": "page-iqc-list",
                          "params": {"status": "检验中"}}]},
            {"id": "ix-drill-review", "name": "下钻：待判定",
             "on": {"event": "click", "target": "n-st-s2"},
             "actions": [{"type": "navigate", "pageId": "page-iqc-list",
                          "params": {"status": "待判定"}}]},
            {"id": "ix-drill-overdue", "name": "下钻：超期未完成",
             "on": {"event": "click", "target": "n-st-s3"},
             "actions": [{"type": "navigate", "pageId": "page-iqc-list",
                          "params": {"overdue": "true"}}]},
            {"id": "ix-drill-ng", "name": "下钻：不合格",
             "on": {"event": "click", "target": "n-st-s4"},
             "actions": [{"type": "navigate", "pageId": "page-iqc-list",
                          "params": {"status": "不合格"}}]},
        ],
        "annotations": [],
        "entryFrom": ["page-iqc-list"],
        "exitTo": ["page-iqc-list"],
        "prd": {"reqIds": ["REQ-IQC-004"], "sections": [
            {"id": "sec-st-1", "heading": "为什么统计单独一页",
             "body": "统计要吃掉 254.75px，在列表页就是 8 行数据。它回答的是「趋势怎么样」，"
                     "与「这一单该怎么办」不是同一个问题，放到一起两边都做不好。"},
        ]},
    }


def build():
    return {
        "meta": {
            "schemaVersion": "1.1",
            "product": "来料检验管理系统",
            "version": "0.1.0",
            "createdAt": "2026-10-22T11:00:00+08:00",
            "updatedAt": "2026-10-22T11:00:00+08:00",
            "reviewMode": False,
            "currentPageId": "page-iqc-list",
            "defaultPanel": "both",
        },
        "product": {
            "name": "来料检验管理系统",
            "oneLiner": "把「这批料能不能用」变成一条可追溯的检验记录。",
            "positioning": "面向锂电材料厂的质检中后台，解决「待检任务在哪、标准是什么、判定归谁」三个问题。",
            "nonGoals": ["不做供应商绩效评分", "不做实验室仪器排程", "不做 SPC 过程控制图"],
            "metrics": [
                {"name": "来料检验及时率", "type": "ratio", "target": "≥ 95%"},
                {"name": "单任务平均处理时长", "type": "duration", "target": "中位数 ≤ 6 小时"},
            ],
        },
        "users": [
            {"id": "u-inspector", "name": "检验员",
             "description": "负责取样、送检、录入检验结果",
             "goals": ["一眼看到今天还有多少待检", "打开任务就知道该按哪个标准做"]},
            {"id": "u-engineer", "name": "质量工程师",
             "description": "负责判定、复检与不合格品处置",
             "goals": ["看到超期与不合格的分布", "判定时能追溯历史批次"]},
            {"id": "u-warehouse", "name": "仓库管理员",
             "description": "负责请验与待检区隔离",
             "goals": ["知道哪些批次已放行"]},
        ],
        "tasks": [
            {"id": "task-iqc-track", "name": "跟踪来料检验任务", "actor": "u-inspector",
             "goal": "找到目标批次并推进到检验中",
             "inputs": ["任务单号 / 批次号 / 物资名称"],
             "doneWhen": "任务已开始检验",
             "pages": ["page-iqc-list"]},
            {"id": "task-iqc-create", "name": "新建检验任务", "actor": "u-inspector",
             "goal": "把请验单转成可执行的检验任务",
             "inputs": ["物资", "批次号", "请验数量"],
             "doneWhen": "任务已保存为待检验",
             "pages": ["page-iqc-new"]},
            {"id": "task-iqc-stats", "name": "查看检验趋势", "actor": "u-engineer",
             "goal": "判断这个月质量在变好还是变坏",
             "inputs": ["时间范围"],
             "doneWhen": "已看清趋势",
             "pages": ["page-iqc-stats"]},
        ],
        "userFlows": [
            {"id": "flow-iqc", "name": "来料检验主流程", "role": "u-inspector",
             "goal": "从请验到放行",
             "steps": [
                 {"id": "fs-1", "name": "新建检验任务", "pageId": "page-iqc-new", "note": "保存为待检验"},
                 {"id": "fs-2", "name": "找到并开始检验", "pageId": "page-iqc-list", "note": "待检验 → 检验中"},
                 {"id": "fs-3", "name": "录入结果并判定", "pageId": "page-iqc-list", "note": "检验中 → 待判定 → 已关闭"},
             ]},
        ],
        "modules": [
            {"id": "m-iqc", "name": "来料检验", "priority": "P0",
             "goal": "覆盖请验、检验、判定与放行的闭环",
             "pageIds": ["page-iqc-list", "page-iqc-new", "page-iqc-stats"]},
        ],
        "pages": [page_list(), page_new(), page_stats()],
        "components": [
            {"id": "c-dense-table", "name": "作业型列表表格", "antd": "Table",
             "spec": "size:'xs' + tableLayout:'fixed' + 每列显式 width；设计行高 32 / 实测 34；1440 档 9 折算行（8 整行）",
             "variants": [{"name": "验收档 866（8 列）"}, {"name": "验收档 1026（同一套 8 列拉伸）"}],
             "states": ["默认", "加载", "空", "零结果", "异常", "超长文本"]},
            {"id": "c-filter-bar", "name": "两行三列筛选区", "antd": "Form",
             "spec": "3 列栅格，label 76 右对齐，控件 240–320，动作独立一行",
             "variants": [{"name": "6 字段两行"}, {"name": "3 字段一行"}, {"name": "收起"}],
             "states": ["展开", "收起"]},
            {"id": "c-drawer", "name": "详情抽屉", "antd": "Drawer",
             "spec": "560 宽，头体脚三件套，关闭后回到原行",
             "variants": [{"name": "w-lg 560"}], "states": ["打开", "关闭"]},
        ],
        "stateMachines": [{
            "id": "sm-iqc", "name": "检验任务状态机", "entity": "InspectionTask",
            "initial": "pending",
            "states": [
                {"id": "pending", "name": "待检验", "type": "warning"},
                {"id": "testing", "name": "检验中", "type": "processing"},
                {"id": "review", "name": "待判定", "type": "normal"},
                {"id": "closed", "name": "已关闭", "type": "disabled"},
            ],
            "transitions": [
                {"id": "t-iqc-1", "from": "pending", "to": "testing",
                 "trigger": "检验员点击「开始检验」", "role": "u-inspector",
                 "guard": "任务未被他人锁定", "action": "记录开始时间并锁定任务",
                 "ui": {"pageId": "page-iqc-list", "interactionId": "ix-start"}},
                {"id": "t-iqc-2", "from": "testing", "to": "review",
                 "trigger": "检验员提交检验结果", "role": "u-inspector",
                 "guard": "全部检验项目均已录入", "action": "生成结果快照并通知质量工程师",
                 "ui": {"pageId": "page-iqc-list", "interactionId": "ix-submit"}},
                {"id": "t-iqc-3", "from": "review", "to": "closed",
                 "trigger": "质量工程师判定合格", "role": "u-engineer",
                 "guard": "所有项目结论为合格", "action": "放行批次并解锁待检区",
                 "ui": {"pageId": "page-iqc-list", "interactionId": "ix-approve"}},
                {"id": "t-iqc-4", "from": "review", "to": "testing",
                 "trigger": "质量工程师判定需复检", "role": "u-engineer",
                 "guard": "至少一项结论不合格", "action": "生成复检任务并保留原始结果",
                 "ui": {"pageId": "page-iqc-list", "interactionId": "ix-recheck"}},
            ],
        }],
        "capabilities": [
            # policy 的语义是「**不可用时怎么办**」（hidden / disabled / reject），
            # 不是「能不能用」。所以「任何时候都可用」= `from: []` + policy 不触发，
            # 而不是发明一个 `enabled` 枚举（那会让 policy 同时表示两件事）。
            {"id": "cap-iqc-create", "name": "新建检验任务", "entity": "InspectionTask",
             "actor": ["u-inspector"], "from": [], "policy": "disabled",
             "effect": "生成待检验任务并回到列表", "page": "page-iqc-new",
             "requirement": "REQ-IQC-001"},
            {"id": "cap-iqc-start", "name": "开始检验", "entity": "InspectionTask",
             "actor": ["u-inspector"], "from": ["pending"], "to": "testing", "policy": "disabled",
             # reason 要写「当前状态 + 允许状态」：只写「状态不允许」会被判笼统 ——
             # 用户看到置灰后唯一想知道的就是「那什么时候能点」。
             "reason": "仅「待检验」可开始检验，当前为「检验中 / 待判定 / 已关闭」",
             "effect": "状态进入检验中并锁定", "page": "page-iqc-list",
             "requirement": "REQ-IQC-002"},
            {"id": "cap-iqc-export", "name": "导出筛选结果", "entity": "InspectionTask",
             "actor": ["u-inspector", "u-engineer"], "from": [], "policy": "disabled",
             "effect": "导出当前筛选下的任务", "page": "page-iqc-list",
             "requirement": "REQ-IQC-003"},
            # 下面四条补的是状态机里那三条「没有按钮可点」的转移 + 统计页的导出。
            # 它们不是为了让校验器闭嘴：缺了它们，读者学到的是一条走到「待判定」就断的流程。
            {"id": "cap-iqc-submit", "name": "提交检验结果", "entity": "InspectionTask",
             "actor": ["u-inspector"], "from": ["testing"], "to": "review", "policy": "disabled",
             "reason": "仅「检验中」可提交检验结果，当前为「待检验 / 待判定 / 已关闭」",
             "effect": "生成结果快照并进入待判定", "page": "page-iqc-list",
             "requirement": "REQ-IQC-005"},
            {"id": "cap-iqc-approve", "name": "判定合格", "entity": "InspectionTask",
             "actor": ["u-engineer"], "from": ["review"], "to": "closed", "policy": "disabled",
             "reason": "仅「待判定」可判定合格，当前为「待检验 / 检验中 / 已关闭」",
             "effect": "放行批次并关闭任务", "page": "page-iqc-list",
             "requirement": "REQ-IQC-005"},
            {"id": "cap-iqc-recheck", "name": "判定需复检", "entity": "InspectionTask",
             "actor": ["u-engineer"], "from": ["review"], "to": "testing", "policy": "disabled",
             "reason": "仅「待判定」可判定需复检，当前为「待检验 / 检验中 / 已关闭」",
             "effect": "生成复检任务并回到检验中", "page": "page-iqc-list",
             "requirement": "REQ-IQC-005"},
            {"id": "cap-iqc-stats-export", "name": "导出统计报表", "entity": "InspectionTask",
             "actor": ["u-engineer"], "from": [], "policy": "disabled",
             "effect": "导出当前时间范围的指标与图表数据", "page": "page-iqc-stats",
             "requirement": "REQ-IQC-004"},
        ],
        "requirements": [
            {"id": "REQ-IQC-001", "pageId": "page-iqc-new", "moduleId": "m-iqc",
             "ui": {"interactionId": "ix-save"},
             "title": "保存检验任务", "pattern": "event-driven",
             "trigger": "检验员填完物资、批次号与请验数量后点击「保存为待检验」",
             "rule": "三个必填项齐全，批次号在 30 天内不得重复建任务",
             "expected": "生成状态为「待检验」的任务并回到列表，列表首行出现该任务",
             "stateMachine": "sm-iqc", "role": "u-inspector",
             "status": "confirmed", "source": "user",
             "acceptance": ["必填项为空时保存被拒绝，提示缺哪一项",
                            "重复批次号保存时提示「该批次已有在检任务」，并给出跳转"]},
            {"id": "REQ-IQC-002", "pageId": "page-iqc-list", "moduleId": "m-iqc",
             "ui": {"interactionId": "ix-start"},
             "title": "开始检验", "pattern": "state-driven",
             "trigger": "检验员在「待检验」任务上点击「开始」",
             "rule": "仅 pending 状态可开始；同一任务不可被两人同时开始",
             "expected": "状态变为「检验中」，开始时间落库，他人界面上的「开始」置灰",
             "stateMachine": "sm-iqc", "role": "u-inspector",
             "status": "confirmed", "source": "user",
             "acceptance": ["非待检验状态下「开始」不可点，并说明当前状态",
                            "两人同时点「开始」时，后到的一方收到「已被某某锁定」"]},
            {"id": "REQ-IQC-003", "pageId": "page-iqc-list", "moduleId": "m-iqc",
             "ui": {"interactionId": "ix-export"},
             "title": "导出筛选结果", "pattern": "event-driven",
             "trigger": "点击标题带的「导出」",
             "rule": "导出范围 = 当前筛选条件，不受分页限制；导出时若单据状态已变更，拒绝导出该行",
             "expected": "生成 xlsx，列与列宽与列表一致",
             "stateMachine": "sm-iqc", "role": "u-inspector",
             "status": "confirmed", "source": "user",
             "acceptance": ["342 条全部导出，不是当前页 20 条",
                            "超长文本列按显示值导出（已截断部分给完整值）",
                            "导出瞬间若该单状态已被他人改变，该行被拒绝并提示「状态已变更，请刷新」"]},
            {"id": "REQ-IQC-004", "pageId": "page-iqc-stats", "moduleId": "m-iqc",
             "ui": {"interactionId": "ix-drill-review"},
             "title": "查看检验趋势并下钻", "pattern": "event-driven",
             "trigger": "进入检验统计页，或点击任一指标卡",
             "rule": "默认本月，可切本周/本季；下钻只允许进入有权限的页面，无权限时拒绝并说明",
             "expected": "四个指标 + 两张图，点击指标下钻到已预填筛选的列表",
             "stateMachine": "sm-iqc", "role": "u-engineer",
             "status": "confirmed", "source": "user",
             "acceptance": ["切换时间范围后指标与两张图同步变化",
                            "点击「待判定」跳到列表且筛选已预填为该状态",
                            "无该模块权限的用户点下钻被拒绝，提示「无权限查看该状态的任务」，不跳页"]},
            # 补一条「推进到判定 / 复检」的需求：cap-iqc-submit / approve / recheck 三条命令
            # 在规范里都要求挂到一条需求上（requirement 字段），而原示例只有 4 条需求，
            # 其中没有一条覆盖「待判定」之后的动作 —— 这是流程断在抽屉里的真正原因。
            {"id": "REQ-IQC-005", "pageId": "page-iqc-list", "moduleId": "m-iqc",
             "ui": {"interactionId": "ix-approve"},
             "title": "提交结果并判定", "pattern": "event-driven",
             "trigger": "检验员在抽屉里点「提交检验结果」，或质量工程师点「判定合格 / 需复检」",
             "rule": "提交仅限「检验中」，判定仅限「待判定」；判定合格需全部项目结论合格",
             "expected": "提交后进入「待判定」；判定合格后关闭并放行，判定需复检后回到「检验中」",
             "stateMachine": "sm-iqc", "role": "u-engineer",
             "status": "confirmed", "source": "user",
             "acceptance": ["非「检验中」状态下「提交检验结果」置灰，并说明当前状态",
                            "非「待判定」状态下「判定合格 / 需复检」置灰；已关闭的单据不可再流转，非法流转被拒绝"]},
        ],
        "boardPlan": [],
        "glossary": [
            {"term": "待判定", "definition": "检验结果已录入但尚未给出合格/不合格结论"},
            {"term": "取样·样品", "definition": "同一格并列两个数：取样件数 / 送检样品件数"},
            {"term": "验收档", "definition": "评审态折叠 PRD 后的内容宽：1440 得 866、1600 得 1026"},
        ],
        "openQuestions": [],
        "dataModel": {"entities": [
            {"id": "e-iqc", "name": "InspectionTask", "table": "inspection_task",
             "description": "来料检验任务主表",
             "pageIds": ["page-iqc-list", "page-iqc-new", "page-iqc-stats"],
             "fields": [
                 {"name": "id", "type": "bigint", "key": "pk"},
                 {"name": "taskNo", "type": "varchar(32)", "required": True, "unique": True,
                  "constraint": "IQC-YYYYMMDD-NNNN"},
                 {"name": "status", "type": "varchar(24)", "required": True,
                  "constraint": "pending|testing|review|closed"},
                 {"name": "material", "type": "varchar(120)", "required": True},
                 {"name": "lot", "type": "varchar(32)", "required": True},
                 {"name": "sampleCount", "type": "int"},
                 {"name": "standard", "type": "varchar(160)"},
                 {"name": "supplierId", "type": "bigint"},
                 {"name": "createdAt", "type": "datetime", "required": True},
             ]},
        ]},
    }


def main():
    data = build()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("wrote %s (%d bytes)" % (OUT, os.path.getsize(OUT)))


if __name__ == "__main__":
    main()
