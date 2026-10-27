# 组件库与状态定义（Ant Design 视觉语言）

> 容器内置一套**Ant Design 风格的渲染器**（纯 HTML/CSS 实现，无 React 依赖），保证单文件离线可用。
> 生成 `componentTree` 时**只能使用本文件白名单内的 `type`**；未知类型会被降级为普通 `div` 并在容器右上角打警告。

---

## 1. 设计令牌（Design Tokens）

写组件时优先用语义 token，容器已内置对应 CSS 变量。

### 1.1 颜色

| Token | 值 | 用途 |
|---|---|---|
| `--ant-primary` | `#1677ff` | 主色、主按钮、链接、选中态 |
| `--ant-primary-hover` | `#4096ff` | 主色悬停 |
| `--ant-primary-active` | `#0958d9` | 主色按下 |
| `--ant-primary-bg` | `#e6f4ff` | 主色浅背景、选中行 |
| `--ant-success` | `#52c41a` | 成功 |
| `--ant-warning` | `#faad14` | 警告 |
| `--ant-error` | `#ff4d4f` | 错误、危险 |
| `--ant-text` | `rgba(0,0,0,.88)` | 主文本 |
| `--ant-text-secondary` | `rgba(0,0,0,.65)` | 次文本 |
| `--ant-text-tertiary` | `rgba(0,0,0,.45)` | 辅助文本、占位符 |
| `--ant-border` | `#d9d9d9` | 边框 |
| `--ant-border-secondary` | `#f0f0f0` | 分割线 |
| `--ant-bg-layout` | `#f5f5f5` | 页面底色 |
| `--ant-bg-container` | `#ffffff` | 卡片/容器底色 |
| `--ant-fill` | `rgba(0,0,0,.04)` | 填充、表头背景 |

> ⚠️ **涨红跌绿**：若原型涉及行情/涨跌数据，涨用 `--ant-error`(红)、跌用 `--ant-success`(绿)，与中国市场惯例一致。

### 1.2 尺寸

| Token | 值 |
|---|---|
| `--ant-radius` | `6px`（按钮/输入框） |
| `--ant-radius-lg` | `8px`（卡片/弹窗） |
| `--ant-font-size` | `14px` |
| `--ant-font-size-sm` | `12px` |
| `--ant-font-size-lg` | `16px` |
| `--ant-control-height` | `32px`（middle）/ `40px`（large）/ `24px`（small） |
| `--ant-line-height` | `1.5714` |
| `--ant-shadow-1` | `0 1px 2px 0 rgba(0,0,0,.03), 0 1px 6px -1px rgba(0,0,0,.02)` |
| `--ant-shadow-2` | `0 6px 16px 0 rgba(0,0,0,.08)`（浮层） |

---

## 2. 组件白名单与属性

> **这一列是「语义承诺」，不是「实现事实」。**
> 容器是逐字段手写读 props 的，表里写了不等于渲染器会读 —— 自 I-11 起，
> **唯一可执行的真相是 props 契约**（`assets/container/props-contract.json`，
> 规则见 `04-container-schema.md` §6.8）。两者不一致时**以契约为准**：
> 差额要么补容器，要么进 `references/props-unsupported.json`，不许两边各说一套。
> 本表尚未逐行按契约核对，剩余差额由 `XX-053` 机械收口。
>
> 已按 I-11 裁决从本表移除的键（写它们不会生效，替代写法见清单）：
> `InputNumber.min/max/step/disabled`、`DatePicker.showTime/disabled`、
> `Upload.multiple/dragger/listType`、`Table.rowKey`、`Descriptions.bordered`、`Alert.banner`。
> 另外两条不在本表、但同样不许写：节点级 `style`（任何类型都不读）、`Alert.text`（正文键是 `message`）。

### 2.1 布局类

| type | props |
|---|---|
| `Layout` | `layout`(`blank`\|`header-content`\|`sider-content`\|`header-sider-content`)、`direction` |
| `Header` | `title`、`logo`(bool)、`back`(bool，渲染返回箭头，内建 back 动作，合成 id `<节点 id>__back`)、`extra`(插槽) |
| `Sider` | `width`(默认 200)、`collapsed`、`title` |
| `Content` | `padding`(默认 24) |
| `Footer` | `text` |
| `Row` | `gutter`、`justify`(`start`\|`center`\|`end`\|`space-between`)、`align`(`top`\|`middle`\|`bottom`) |
| `Col` | `span`(1–24)、`offset` |
| `Space` | `direction`(`horizontal`\|`vertical`)、`size`(默认 8)、`wrap`、`align`、`split` |
| `Divider` | `text`、`dashed`、`orientation`(`left`\|`center`\|`right`) |

### 2.2 导航类

| type | props |
|---|---|
| `Menu` | `mode`(`vertical`\|`horizontal`\|`inline`)、`selectedKey`、`items`(`[{key,label,icon,disabled}]`) |
| `Breadcrumb` | `items`(`[{label,href}]`) |
| `Tabs` | `activeKey`、`items`(`[{key,label,disabled,badge}]`)、`type`(`line`\|`card`) |
| `Steps` | `current`(0 起)、`items`(`[{title,description}]`)、`direction`、`status`(`process`\|`error`) |
| `Pagination` | `current`、`total`、`pageSize`、`showSizeChanger` |
| `Dropdown` | `text`、`items`(`[{label,danger,divider}]`)、`trigger` |
| `Segmented` | `options`(`[string]`)、`value` |

### 2.3 数据录入类

| type | props |
|---|---|
| `Button` | `text`、`type`(`primary`\|`default`\|`dashed`\|`text`\|`link`)、`size`、`danger`、`disabled`、`disabledReason`、`loading`、`block`、`icon`、**`capability`**（引用 `capabilities[].id`，可用性由角色 × 状态求值） |
| `Input` | `placeholder`、`value`、`prefix`、`suffix`、`size`、`disabled`、`allowClear`、`status`(`error`\|`warning`) |
| `TextArea` | `placeholder`、`rows`、`value`、`maxLength`、`showCount` |
| `InputNumber` | `value` |
| `Select` | `placeholder`、`value`、`options`(`[{label,value,disabled}]`)、`mode`(`multiple`)、`disabled`、`allowClear` |
| `Checkbox` | `label`、`checked`、`disabled` |
| `CheckboxGroup` | `options`、`value`(`[string]`)、`direction` |
| `Radio` | `label`、`checked`、`disabled` |
| `RadioGroup` | `options`、`value`、`buttonStyle`(bool 表示按钮组) |
| `Switch` | `checked`、`disabled`、`checkedText`、`unCheckedText`、`size` |
| `DatePicker` | `placeholder`、`value` |
| `TimePicker` | `placeholder`、`value` |
| `Upload` | `text`、`accept` |
| `Form` | `layout`(`horizontal`\|`vertical`\|`inline`)、`labelWidth` |
| `FormItem` | `label`、`required`、`help`(校验结果，随 `validateStatus` 变色)、`extra`(常态说明，12px、`--ant-text-3`（与 `help` 同色；**不用 `--ant-text-4`**，那是 placeholder 级，12px 下看不清）；与 `help` 可同时出现，`help` 在上)、`validateStatus`(`error`\|`warning`\|`success`\|`validating`) |
| `Slider` | `value`、`min`、`max`、`marks` |
| `Rate` | `value`、`count` |
| `Cascader` | `placeholder`、`options`(`[{value,label,children}]`) |
| `Transfer` | `dataSource`(`[{key,title}]`)、`targetKeys` |

> **按钮可用性不要写死 `disabled`**：业务按钮声明 `props.capability`（表格行内用
> `columns[].actions[].capability`），容器按「当前角色 × 当前单据状态」求值，得到四种表现：
>
> | 表现 | 触发条件 | 视觉 |
> |---|---|---|
> | 可用 | 当前状态 ∈ `capability.from` | 正常 |
> | 置灰 | 不满足且 `policy: "disabled"` | 灰底灰字 + 悬浮/点击说明 `reason` |
> | 隐藏 | 不满足且 `policy: "hidden"` | 不渲染 |
> | 虚线警告 | 不满足且 `policy: "reject"` | 正常外观 + 警告色虚线，点了才拒绝 |
>
> 纯查看类动作（详情、打印、复制单号）覆盖全部状态时，不必写 `capability`。
> 契约见 `04-container-schema.md` §8.5，方法见 `09-behavior-model.md`。

### 2.4 数据展示类

| type | props |
|---|---|
| `Table` | `columns`(`[{title,dataIndex,width,align,type:'text'\|'tag'\|'avatar'\|'action'\|'progress'\|'index',actions?}]`)、`data`(`[{}]`)、`loading`、`empty`、`emptyText`、`bordered`、`size`、`rowSelection`、`radio`、`rowClick`、`title` |
| `Table` · 列表页三件套 | `query`(`[{label,type,props,placeholder}]` 查询条件区)、`queryExtra`(bool，默认 true，渲染「设置查询字段 / 搜索 / 展开」)、`queryActions`(`[{text,type,icon,id}]` 追加到查询条右侧)、`toolbar`(`[{text,type,icon,disabled,id}]` 或 `[{type:'Button',id,props}]`)、`toolbarRight`(bool，默认 true，渲染列设置图标)、`toolbarRightItems`、`pagination`(`{total,pageSize,current,maxShow,jump}` 或 `true`) |
| `Table` · 密度与吸附（v0.8.0 新增） | `size`(`'xs'`\|`'small'`，渲成 `.xs` / `.sm` 类；**没有 `'sm'` 这个值**，`'sm'` 是类名)、`tableLayout`(`'fixed'`)、`stickyHeader`(bool，**须与 `maxHeight` 同时给**才生成吸附容器)、`stickyFooter`(bool，配合 `pagination` 把分页脚贴底)、`maxHeight`(CSS 长度，如 `calc(100vh - 438px)`，写进 `--tw-max`)、`rowClick`(bool，整行点击触发)、`ellipsisTitle`(bool，默认 true，截断列的 `title` 兜底) |
| `Table` · 筛选区渲染器（v0.8.0 新增） | `filterBar`(`'grid3'` = 两行三列 + 独立动作行；**不写则沿用旧 `query` 单行路径**)、`queryId` / `resetId`(字符串，写入「查询 / 重置」按钮的 `data-node-id`，可被 `interactions.on.target` 引用) |
| `Table` · 空态（v0.8.0 新增） | `emptyAction`(`{text, type?, icon?, id}`，渲染在空态文案下方；`text` 必填、`id` 用于挂交互)。空态（没有数据）与零结果（筛没了）必须用**不同的 `emptyText` 与 `emptyAction`** |
| `Table` · 列定义补充（v0.8.0 新增；v0.9.0 补 `wrap`/`maxLines`） | `columns[]`：`width`(纯数字按 px 处理；**字符串必须自带单位**，写 `'48'` 会被浏览器丢弃。两种写法等价，**判据必须都认** —— 视觉判据用 `float(w)` 单种解析会把 `'150px'` 判成「未声明」)、`ellipsis`(bool，配 `cell-ellipsis`)、`wrap`(bool，允许换行，须与 `maxLines` 同时给)、`maxLines`(**只允许 2**；≥3 会把行高预算吃光)、`fix`(`'left'`\|`'right'`)、`num`(bool，`tabular-nums` 右对齐)、`align`(`'left'`\|`'right'`) |
| `MasterDetail` | `bind`(主表字段名)、`bindTo`(子表字段名，默认同 `bind`)、`detailTitle`、`collapsible`(默认 true)、`defaultCollapsed`、`autoSelectFirst`(默认 true)、`showAllWhenEmpty`、`emptyText`、`detailTools`(`[{text,icon,id}]`)；**children 必须正好 2 个**：`[主表 Table, 子表 Table]` |
| `List` | `data`、`renderItem`(Node 模板，写在 **props 内**；占位 `{{item.字段}}` / `{{item}}` / `{{index}}`)、`bordered`、`loading`、`empty`、`size` |
| `List.Item` | `title`、`description`、`extra`(插槽)、`avatar` |
| `Card` | `title`、`bordered`(`true` → 1px 边框 + 无投影，满足 `12` `L-02`)、`hoverable`、`size`、`loading`；插槽 `extra`、`cover`、`actions` |
| `Descriptions` | `title`、`column`、`items`(`[{label,value,span}]`) |
| `Tag` | `text`、`color`(`default`\|`blue`\|`green`\|`red`\|`orange`\|`purple`\|`cyan`\|`success`\|`processing`\|`error`\|`warning`)、`closable` |
| `Badge` | `count`、`status`、`text`、`dot`、`color` |
| `Avatar` | `text`、`src`、`size`(数字或 `small`\|`large`)、`shape`(`circle`\|`square`) |
| `Tooltip` | `title`、`placement` |
| `Collapse` | `items`(`[{key,label,content}]`)、`accordion`、`activeKey` |
| `Timeline` | `items`(`[{content,time,color}]`) |
| `Tree` | `data`(`[{title,key,children}]`)、`checkable`、`defaultExpandAll`、`selectedKeys` |
| `Statistic` | `title`、`value`、`prefix`、`suffix`、`precision`、`trend`(`up`\|`down`) |
| `Empty` | `description`、`image`(`simple`) |
| `Progress` | `percent`、`type`(`line`\|`circle`)、`status`(`normal`\|`active`\|`success`\|`exception`)、`showInfo` |
| `Skeleton` | `rows`、`avatar`、`active` |
| `Alert` | `message`(正文，**不是 `text`**)、`description`、`type`(`success`\|`info`\|`warning`\|`error`)、`showIcon`、`closable`、`visible`(通用键，所有节点都认) |
| `Image` | `src`、`alt`、`width`、`height`、`placeholder` |
| `Carousel` | `items`(`[{title,text}]`)、`autoplay` |
| `Calendar` | `value`、`mode`(`month`\|`year`)、`marks` |
| `Tag` (status map) | 见 §4 |

### 2.5 反馈类

| type | props |
|---|---|
| `Modal` | `title`、`open`、`width`、`okText`、`cancelText`、`footer`(bool)、`content`、`confirmLoading`、`centered`；底部按钮合成 id `<节点 id>__ok` / `__cancel`（`__cancel` 内建关闭弹窗） |
| `Drawer` | `title`、`open`、`placement`(`right`(默认)\|`left`\|`top`\|`bottom`；`top`/`bottom` 满宽、限高 70%、**不吃 `width`**)、`width`、`content`、`footer`(插槽) |
| `Drawer` · 宽档（v0.8.0 补充） | `width` 取 **560** 时为「详情抽屉」档（渲成 `.ant-drawer.w-lg`，默认 420）。**声明宽必须由渲染器读**：`R.Drawer` 读 `p.width`，≥560 走 `.w-lg`、其它数值用 inline，不写才吃默认 420 —— 漏读就会退回 420。**视觉档位只有 420 / 560 两个**（**不是**说允许值只有两个：`0 < 宽 < 560` 走 inline、声明几渲几，`440` / `520` 合法且 `example-01` / `04` / `05` 正在用）：`width:600` 会渲成 560、`"600px"` 会被 `Number()` 成 NaN 而回 420 —— 两种都是「声明 ≠ 渲染」，由 `04 §6.8` 的 R6 判 ERROR。验收必须打开抽屉量 `offsetWidth`，只贴 JSON 的 `width: 560` 不算证据（为什么与怎么量见 `08-container-choice.md` §0.8） |
| `Popconfirm` | `title`、`description`、`okText`、`cancelText` |
| `Spin` | `size`、`tip`、`spinning` |
| `Result` | `status`(`success`\|`error`\|`info`\|`warning`\|`404`\|`403`\|`500`)、`title`、`subTitle`；插槽 `extra` |

### 2.6 排版与原型辅助

| type | props |
|---|---|
| `Typography` | `text`、`level`(1–5)、`type`(`secondary`\|`success`\|`warning`\|`danger`)、`strong`、`italic`、`code`、`ellipsis`、`delete`、`mark` |
| `Paragraph` | `text`、`type` |
| `Text` | `text`、`type`、`strong` |
| `Icon` | `name`（内置图标集，见 §5）、`size`、`color` |
| `Placeholder` | `text`、`height`、`dashed`（灰色占位块，用于"此处待定"） |
| `Chart` | `type`(`bar`\|`line`\|`pie`\|`donut`)、`data`(`[{label,value}]`)、`height`、`title` |
| `Frame` | `width`、`height`、`label`、`scroll`（设备框，用于移动端原型） |
| `Modal`/`Drawer` 触发 | 通过 `interactions` 的 `showModal`/`showDrawer` action |

---

## 3. 组件级状态（Component State）

Node 的 `state` 字段取值与渲染规则：

| state | 视觉规则 | 适用组件 |
|---|---|---|
| `normal` | 默认 | 全部 |
| `hover` | 加 `--ant-primary-hover` 边框 / 浅色底 | Button、Card、List.Item、Table 行 |
| `active` / `selected` | `--ant-primary-bg` 底 + 主色边框 | Menu、Tabs、List.Item、Table 行 |
| `loading` | 骨架屏 / Spin / 按钮转圈 | Button、Table、List、Card、Skeleton |
| `disabled` | 透明度 `.45` + `not-allowed` 光标 | Button、Input、Select、Checkbox… |
| `error` | 边框 `--ant-error` + 底部红字 | Input、Select、FormItem |
| `warning` | 边框 `--ant-warning` | Input、FormItem |
| `success` | 边框/图标 `--ant-success` | FormItem、Result |
| `empty` | 空状态插图 + 文案 | Table、List、Card |

**业务状态 → 视觉映射（业务状态色板）**：业务状态（如"待办/进行中/阻塞/完成"）不要直接写死颜色，用下面的映射：

| 语义 | Tag color | 色值 | 例子 |
|---|---|---|---|
| 中性/未开始 | `default` | `#fafafa`/`#8c8c8c` | 待办、草稿 |
| 进行中 | `processing` | `#1677ff` | 处理中、审核中 |
| 成功/完成 | `success` | `#52c41a` | 已完成、已通过 |
| 警告/阻塞 | `warning` | `#faad14` | 阻塞、待补充 |
| 失败/拒绝 | `error` | `#ff4d4f` | 已驳回、异常 |
| 特殊/强调 | `purple`/`cyan` | `#722ed1`/`#13c2c2` | 加急、VIP |

---

## 4. 状态机 → 原型 的落地约定

1. 状态机的每个 `state` 在原型里必须**可见**：用 `Tag`/`Badge` 或状态条展示当前状态。
2. 每个 `transition` 对应**至少一个可触发元素**（按钮/开关/菜单项），并在 `interactions` 里定义 `setState` 改状态变量。
3. 状态机不允许出现**孤立状态**（无入边或无出边，除终态）。
4. 页面 `states` 至少要有一个覆盖**异常分支**（`unwanted` 类需求）。

---

## 5. 内置图标集（`Icon.name`）

`plus` `edit` `delete` `search` `filter` `setting` `user` `team` `bell` `check` `close` `arrow-right` `arrow-left` `arrow-down` `chevron-down` `chevron-right` `more` `menu` `home` `folder` `file` `calendar` `clock` `tag` `star` `heart` `download` `upload` `export` `refresh` `info` `warning` `error` `success` `loading` `drag` `eye` `lock` `unlock` `link` `chart` `dashboard` `list` `grid` `play` `pause` `stop` `send` `copy` `external` `filter-active`

> 图标用内联 SVG 渲染，保证离线可用。需要未列出的图标时，用 `Placeholder` 或最近的语义图标替代。

---

## 6. 常见页面骨架模板（可直接抄）

### 6.1 中后台列表页（header-sider-content）

```jsonc
{ "id":"n-root","type":"Layout","props":{"layout":"header-sider-content"},"children":[
  { "id":"n-header","type":"Header","props":{"title":"任务看板","logo":true},
    "slots":{"extra":[{"id":"n-avatar","type":"Avatar","props":{"text":"PM"}}]} },
  { "id":"n-sider","type":"Sider","props":{"width":200},
    "children":[{"id":"n-menu","type":"Menu","props":{"mode":"inline","selectedKey":"tasks","items":[
      {"key":"home","label":"概览","icon":"dashboard"},
      {"key":"tasks","label":"任务","icon":"list"},
      {"key":"settings","label":"设置","icon":"setting"}]}}]},
  { "id":"n-content","type":"Content","children":[
    { "id":"n-toolbar","type":"Space","props":{"size":8},"children":[
      {"id":"n-search","type":"Input","props":{"placeholder":"搜索任务","prefix":"search"}},
      {"id":"n-btn-new","type":"Button","props":{"text":"新建任务","type":"primary","icon":"plus"}}]},
    { "id":"n-table","type":"Table","props":{"bordered":false,"columns":[
      {"title":"任务","dataIndex":"title"},
      {"title":"状态","dataIndex":"status","type":"tag"},
      {"title":"负责人","dataIndex":"owner","type":"avatar"},
      {"title":"操作","type":"action"}],
      "data":[{"title":"完成 PRD","status":"进行中","owner":"张"}]}}]}
]}
```

### 6.2 移动端表单页（Frame 包裹）

```jsonc
{ "id":"n-frame","type":"Frame","props":{"width":375,"height":700,"label":"iPhone"},"children":[
  { "id":"n-nav","type":"Layout","props":{"layout":"header-content"},"children":[
    { "id":"n-navbar","type":"Header","props":{"title":"新建任务","back":true} },
    { "id":"n-form","type":"Content","children":[
      { "id":"n-fi1","type":"FormItem","props":{"label":"任务标题","required":true},
        "children":[{"id":"n-in1","type":"Input","props":{"placeholder":"请输入"}}]},
      { "id":"n-btn","type":"Button","props":{"text":"提交","type":"primary","block":true}} ]} ]}
]}
```

### 6.3 可跳转列表页（行级跳转 + 行内按钮，推荐写法）

要点：`rowClick: true` 让行可点；操作列用 `actions` 声明按钮 key；**一条通配 interaction 覆盖所有行**；params 用 `{{row.字段}}` 按行取值。

```jsonc
// 列表页
{
  "id": "n-table", "type": "Table", "props": {
    "rowClick": true,
    "columns": [
      { "title": "商品", "dataIndex": "name" },
      { "title": "状态", "dataIndex": "status", "type": "tag" },
      { "title": "操作", "type": "action", "actions": [
        { "key": "view", "label": "查看" },
        { "key": "off",  "label": "下架", "type": "danger" } ] } ],
    "data": [ { "name": "轻量羽绒外套", "sku": "GD-1001", "status": "已上架" } ]
  }
}
```

```jsonc
// 同一页的 interactions
[
  { "id": "ix-row", "name": "点行查看详情",
    "on": { "event": "click", "target": "n-table__row_*" },        // ← 通配：任意一行
    "actions": [{ "type": "navigate", "pageId": "page-goods-detail",
                  "params": { "goodsName": "{{row.name}}", "goodsSku": "{{row.sku}}" } }] },

  { "id": "ix-off", "name": "下架",
    "on": { "event": "click", "target": "n-table__act_*_off" },     // ← 通配：任意一行的「下架」
    "actions": [{ "type": "message", "level": "warning", "text": "已下架：{{row.name}}" }] }
]
```

> 因为容器用 `closest('[data-node-id]')` 就近命中，点「下架」**不会**同时触发整行跳转——两条 interaction 可以共存，不需要额外处理。

```jsonc
// 详情页：接收带参跳转（并给自己留默认值，单独打开也正常）
{
  "id": "page-goods-detail",
  "componentTree": { "id": "n-root", "type": "Layout", "props": { "layout": "header-content" },
    "children": [
      { "id": "n-header", "type": "Header", "props": { "title": "商品详情", "back": true } },  // ← 返回箭头内建
      { "id": "n-desc", "type": "Descriptions", "props": { "items": [
        { "label": "商品名称", "value": "{{goodsName}}" },
        { "label": "商品编码", "value": "{{goodsSku}}" } ] } } ] },
  "states": [
    { "id": "s-default", "name": "默认态",
      "vars": { "goodsName": "轻量羽绒外套", "goodsSku": "GD-1001" } }   // ← 默认值兜底
  ]
}
```

### 6.4 主子表页面（主表选行 → 子表联动，推荐写法）

**什么时候用**：单页面数据层级较多 —— 一条主记录下挂着若干明细，用户需要边扫主表、边看某一条的明细。
（一条巡检任务 → 若干巡检项；一张订单 → 若干商品行；一台设备 → 若干保养记录。）

要点：`MasterDetail` 的 children **必须正好 2 个 Table**；主表开 `radio` 标出当前行；
`bind` / `bindTo` 写清两表的关联字段；**主表不要设 `rowClick`**（点行 = 选中行，跳页请用操作列按钮）。

```jsonc
{
  "id": "n-md-task", "type": "MasterDetail", "props": {
    "bind": "no", "bindTo": "taskNo",       // 主表 no ↔ 子表 taskNo
    "detailTitle": "巡检项",
    "collapsible": true,                     // 子表可展开收起
    "autoSelectFirst": true,                 // 默认选中首行，子表不空
    "emptyText": "请先在上方选择一条巡检任务"
  },
  "children": [
    { "id": "n-task-table", "type": "Table", "props": {
        "title": "巡检任务",
        "radio": true,                                    // ← 单选圆点列
        "query": [ { "label": "任务编号", "type": "Input" },
                   { "label": "状态", "type": "Select",
                     "props": { "options": [{ "value": "doing", "label": "巡检中" }] } } ],
        "toolbar": [ { "text": "新增", "type": "primary", "icon": "plus", "id": "n-btn-new" },
                     { "text": "导出", "icon": "download" } ],
        "columns": [
          { "title": "序号", "type": "index", "width": "56px" },
          { "title": "任务编号", "dataIndex": "no" },
          { "title": "状态", "dataIndex": "status", "type": "tag" },
          { "title": "操作", "type": "action", "actions": [
            { "key": "detail", "label": "详情" }, { "key": "edit", "label": "修改" } ] } ],
        "data": [ { "no": "ONSETE-20261016-0043", "status": "巡检中" } ],
        "pagination": { "total": 36927, "pageSize": 10, "current": 1, "jump": true } } },

    { "id": "n-item-table", "type": "Table", "props": {
        "title": "巡检项",
        "emptyText": "该任务暂无巡检项",
        "columns": [ { "title": "序号", "type": "index" },
                     { "title": "巡检项编号", "dataIndex": "no" },
                     { "title": "巡检状态", "dataIndex": "status", "type": "tag" } ],
        "data": [ { "no": "XJ-20251209002", "taskNo": "ONSETE-20261016-0043", "status": "待巡检" } ] } }
  ]
}
```

> **子表的 `data` 写全量**（所有任务的明细），容器按 `bind` 自动过滤。不要把过滤后的数据预先写进子表。
>
> 跳页仍走主表操作列：`{ "on": { "target": "n-task-table__act_*_detail" }, "actions": [{ "type": "navigate", ... }] }`。
>
> 完整可运行示例：`assets/examples/example-04-master-detail.json`。

