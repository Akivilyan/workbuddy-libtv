# LibTV 平台能力索引

> **本文管什么**：平台上**有什么、在哪、三个入口对不对得上** —— 这类信息官方手册不写、静态文档查不到，只能现场从云端配置拉。
> **与出片规范的分工**：`wan3.0×LibTV-出片规范.md` 管「一个镜头怎么做出好画面」；本文管「平台有哪些能力和口子」。
> **取证**：CLI **1.1.3**，实测日 **2026-09-23**。凡标「未实测」的，是文档/配置所述但未跑过。

---

## 1. 云端配置入口（唯一查法）

```
https://api2.liblib.art/api/www/landing-activities/getById?id=<N>
```

响应 `data.linkUrl` 是一个 **JSON 字符串**（二次解析）。全部已知 id：

| id | 内容 | 用途 |
|---|---|---|
| **240** | `{ version, install:{CMD,PowerShell,shell}, skill }` | ★ **CLI 最新版本号的唯一权威** |
| **186** | 运镜预设（4 类 29 项，含英文 prompt 片段） | 已固化：`LibTV运镜预设-config186.md` |
| **127** | 特效白名单（`params.template` 取值） | 透传用，**无 schema 校验** |
| **188** | `slashImage`（17 条）+ `slashPresetCategory`（4 类）+ `character`（角色库筛选维度） | ★ 图片 Slash 定义；见 §4 |
| **243** | `styleModelList`（风格模板）+ `lensModelList`（镜头库） | 风格/镜头选型 |

⚠️ **`…/cli/latest/manifest.json` 已停更**（仍返回 `1.0.2`）→ 照它走会**把 CLI 降级**。版本号一律走 id 240。

---

## 2. 账号与通道

### 2.1 登录

```bash
libtv login web --open          # 浏览器登录，凭据落 ~/.libtv/credentials.json
libtv account info              # ★ 成功退出才算登录（project list 为空 ≠ 未登录）
libtv account list / account use  # 多账号切换（团队场景才用）
```

### 2.2 三条通道

| 通道 | 入口 | 定位 |
|---|---|---|
| **CLI** | `libtv.exe` | ★ **主力** —— 画布/节点/连线/生成全能，且有 Slash 封装 |
| **MCP** | `https://mcp.liblib.tv/mcp` | **互补** —— 48 工具；有 CLI 没有的异步与预检能力 |
| Plugin | Codex 专属 | 本机不用 |

### 2.3 ⚠️ 官方 GitHub 仓库是废弃通道

`libtv-labs/libtv-skills`：**7 次提交全在 2026-03-16~18，此后停摆**；用 `LIBTV_ACCESS_KEY` 走 `im.liblib.tv` —— **即已废弃的旧 OpenAPI 通道**，与 CLI 无关。1097★ / 10 个 open issue 官方基本不回。

- 但 issue 里的两点在 CLI 时代**仍成立**：① Agent 自动跑会**黑盒烧积分**；② **后端会重写 prompt**（见 §6）。
- 已知 issue 摘录：#1「开了一个月订阅……积分消耗过半（1900→500），调用过程透明化做得太差」、#9「充了年费还得在控制台自己点啊拖的」。

### 2.4 CLI 能力边界

- **查不到余额 / 积分单价**（`account info` 不含，schema 无价格字段）→ 只能网页控制台看。
- 没有：成片导出、媒体理解、Script V2、Agent 委托 —— 这些在 MCP。
- **CLI 没有自更新**，`--version` 只报自己。

---

## 3. 计价（2026-09 实测折算）

| 项 | 值 |
|---|---|
| 视频单价 | **8 积分/秒**（720P；10s 带音频 = 80 积分） |
| 音频 | **不计费** |
| 分辨率 | 越高越贵 |
| 花费决定因素 | **总时长 × 重生成次数** —— 与「切几刀」无关 |

⇒ 推论：**1 次 15s 与 3 次 5s 花费相同**，差别只在返工粒度。这是「多镜头公式 + 视频延长」成为最优解的原因。

⚠️ **图片的积分单价我查不到**（schema 里没有价格字段）。「用图省视频积分」这笔账要自己在网页核一次图片计价才算得出来。
⚠️ **会员套餐积分单价从不公布**（年付 499/1299/2999/6599 元），上表「折算」是基于总价÷总积分，**不是官方单价**。
⚠️ 第三方称「会员积分有效期 31 天」——**未核实**。

---

## 4. 图片生成

### 4.1 入口

```bash
libtv image shortcut list                 # ★ 列出现场可用的 Slash（权威）
libtv image shortcut <scene> ...          # 执行
```

⚠️ **17 条 Slash 在任何静态文档里都没有** —— 它们定义在云端配置 `188`，**必须 `shortcut list` 现场拉**。

### 4.2 Slash 全表（17 条，云端定义）

`inputRequirement` 含义：`prompt` = 纯文生｜`prompt_or_image` = 文生或图生｜**`image` = 必须有参考图**。

| # | scene | 名称 | 输入 | 默认清晰度 | 说明 |
|---|---|---|---|---|---|
| 1 | `storyboard_canvas_skill_new` | 调度故事板 | prompt | 4K | 带运动轨迹等调度草图分镜，整理为 **4-6 个中文手绘分镜** |
| 2 | `storyboard_canvas_skill` | 故事板 | prompt | 4K | 整理为 **4-8 个连续分镜**，过长自动提炼关键剧情 |
| 3 | `continuous_storyboard_grid_25` | 25宫格连贯分镜 | prompt_or_image | 4K | 连续分镜长图 |
| 4 | `story_beat_grid_4` | 剧情推演四宫格 | prompt_or_image | 4K | 四格剧情推演 |
| 5 | `frame_prediction_plus_3s` | 画面推演 - 3秒后 | **image** | 4K | 基于物理逻辑推演 3 秒后 |
| 6 | `frame_prediction_minus_5s` | 画面推演 - 5秒前 | **image** | 4K | 反推 5 秒前状态 |
| 7 | `portrait_texture_adjustment` | 人像质感调节 | prompt_or_image | 2K | ★ **降低 AI 感**，优化人物质感与光影 |
| 8 | `cinematic_lighting_correction` | 电影级光影校正 | **image** | 4K | 调整画面光影质感 |
| 9 | `720_panoramic` | 720全景 | prompt_or_image | 2K | 全景场景图 |
| 10 | `multi_camera_grid_9` | 多机位九宫格 | **image** | 4K | 约 9 个不同角度/景别 |
| 11 | `multi_camera_grid_9_4k` | 多机位九宫格4K | **image** | 4K | 同上，固定 4K |
| 12 | `character_turnaround_3view` | 角色三视图 | prompt_or_image | 4K | 正/侧/背 + 脸部特写（白底） |
| 13 | `character_face_turnaround_3view` | 角色脸部三视图 | prompt_or_image | 2K | 脸部细节三视图（白底） |
| 14 | `character_setting_sheet` | 角色设定图 | prompt_or_image | 4K | **角色主视觉与设定拆解** ← 记忆中「全视角+表情+衣物一套图」对应这条 |
| 15 | `scene_setting_sheet` | 场景设定图 | prompt_or_image | 4K | 场景主视觉与设定拆解 |
| 16 | `product_setting_sheet` | 产品设定图 | prompt_or_image | 4K | 产品主视觉与设定拆解 |
| 17 | `product_turnaround_3view` | 产品三视图 | prompt_or_image | 4K | 产品多角度与细节拆解 |

**官方原文（来自 `storyboard_canvas_skill` 的占位文案）**：

> 描述一个 10-15 秒内能演完的小剧情片段，系统会整理为 4-8 个连续分镜……**提供角色三视图、美术设定图及准确的需求描述，生成效果会更好。**

⇒ 官方自证：**三视图与设定图是故事板的上游输入**。这条链是设计出来的，不是巧合。

⚠️ **没有独立的「武器」「衣物」指令** —— 靠 `character_setting_sheet`（设定拆解）或 prompt 定向。别去翻那个不存在的按钮。

### 4.3 四个官方分类（`slashPresetCategory`）

| 分类 | 含 |
|---|---|
| **分镜叙事** | 调度故事板 · 故事板 · 25宫格 · 四宫格 · 推演+3s · 推演-5s |
| **质感调节** | 人像质感调节 · 电影级光影校正 |
| **空间与机位** | 720全景 · 多机位九宫格 |
| **设定图** | 角色脸部三视图 · 角色设定图 · 角色三视图 · 场景设定图 · 产品设定图 |

⚠️ **分类只登记了 15 条**：`multi_camera_grid_9_4k` 与 `product_turnaround_3view` **未进任何分类**（前者 `showIn` 只有 `agent_slash`）。

### 4.4 模型兼容性（★ 选错会不支持）

`supportModels` 实测：

| 适用范围 | 支持模型 |
|---|---|
| 多数 Slash | `lib-image-2` · `nebula-ultra` · `nebula-2-flash` |
| **两条故事板** | ⚠️ **仅 `lib-image-2`** |
| **720全景** | ⚠️ **仅 `lib-image-2` · `nebula-2-flash`**（**不含 `nebula-ultra`**）|

⚠️ **潜在坑**：全部 17 条的 `match.model` 默认值都写着 `nebula-ultra`，**但 `720_panoramic` 的 `supportModels` 并不含它** —— 默认值与兼容列表不一致，此处**未实测**，用前先确认。

### 4.5 图片模型目录

| 来源 | 数量 |
|---|---|
| CLI `model search --type image` | **18 个** |
| MCP `search_models(nodeType=image)` | **26 个** |

⇒ **全量查 MCP，Slash 走 CLI。**

CLI 侧 18 个（modelKey / modelName / 约耗时）：

| modelKey | modelName | 耗时 | 定位 |
|---|---|---|---|
| `lib-image-2.5-s` | Lib Image 2.5 Pro | 30s | 精准生成与编辑 |
| `lib-image-2.5-f` | Lib Image 2.5 Fast | 20s | 极速 |
| `lib-image-2` | Lib Image | 60s | **长文本能力突出**（Slash 的主力底座）|
| `nebula-ultra` | General image Pro | 50s | 最强图片编辑，**一致性好** |
| `nebula-2-flash` | General image V2 | 25s | 支持联网搜索，速度快 |
| `doubao-seedream-5-0-pro` | Seedream 5.0 Pro | 20s | 精准交互式编辑 |
| `qwen-image-3` | Qwen image 3.0 | 60s | 复杂版面与精准文字 |
| `mj-v8.2` / `mj-v8.1` / `mj-v7` / `mj-niji7` | Style Image 系列 | 50s | 美学/电影质感/动漫 |
| `jimeng-4.6` | Seedream 4.6 | 20s | 提升**人像一致性** |
| `seedream-5` | Seedream 5.0 Lite | 20s | 中式风格 |
| `seedream-4.5` | Seedream 4.5 | 15s | **多角色一致性** |
| `z-image` | Z-image Turbo | 10s | 极速写实 |
| `qwen` / `qwen-edit` | Qwen Image / Edit | 60s | 文字排版 / 精细编辑 |
| `seedream-4` | Seedream 4.0 | 15s | 中文文字与海报 |

★ **「一致性」已是模型能力标签**，不只是靠堆素材：`nebula-ultra`「一致性好」· `seedream-4.5`「多角色一致性」· `jimeng-4.6`「人像一致性」。

MCP 比 CLI 多出的（含）：`nebula-core` · `orbit-2-image`（Shock Image 2，电影质感强）· `flux-2-pro` / `flux-2-flex` / `flux-1` · `image-editor` / `image-editor-pro`（局部精准改图）。

⚠️ **同一模型两处描述不一致**：`nebula-ultra` —— CLI 说「最强图片编辑模型，一致性好」，MCP 说「最强图片模型，媲美 Nano pro 模型」。

### 4.6 三个坑

1. ★ **九宫格/25宫格/故事板的产物是「一张拼图」，不是 9 张图。** 喂进 `mixed2video` 时被当**一张图**理解（模型看到的是「一张有 9 个小人的图」，不是 9 个机位）→ **必须本地裁成单图**，再按压镜挑 2-3 张。
2. **CLI 侧 `-n` 必填**（节点名），且手册称该节点须具备参考图（入边或自身已有 http(s) 图）。⚠️ 它与 `inputRequirement` 的对应关系**未逐一实测** —— 理论上 `prompt` / `prompt_or_image` 的 13 条应可纯文生（一跳），`image` 的 4 条必须两跳。
3. **CLI 少一条**：`shortcut list` 实测 **16 条**，云端配置 **17 条** —— **缺 `720_panoramic`（720全景）**。要用得走网页端。

### 4.7 CLI vs MCP 分工（互补，不是替代）

| 能力 | CLI | MCP |
|---|---|---|
| Slash 快捷（17 条封装） | ✅ `image shortcut` | ❌ **无** |
| 图片生成提交 | `node create -t image --run`（**同步阻塞到终态**） | ✅ `generation_submit(kind="image")` → **立即返 `task_id`** |
| 任务查询 / 取消 | ❌ | ✅ `task_status` / `task_cancel` |
| **写库前参数校验** | ❌ 跑一遍才知道 | ✅ 原文「an invented model or an out-of-range value is **rejected before any write**」 |
| 生成计划预检 | ❌ | ⚠️ `validate_generation_plan` **只收 video** → **图片没有预检** |

**未实测通路（零成本可验）**：Slash 本质就是给 image 节点写一组 params（CLI 手册原文「合并 Slash params，`prompt` 强制为 `/`」）⇒ `create_node(params={"scene": "multi_camera_grid_9", "prompt": "/"})` **可能**等效于 `image shortcut`。不确定点：`scene` 不在 `nebula-ultra` 的 model schema 里（该 schema 有 `enableSlash: true` 但无 `scene`）→ MCP 的写库前校验会不会拒绝这个额外字段，只能实测。

---

## 5. 分镜链路（`script` / `storyboard` 节点）

### 5.1 `script` 节点 = 结构化分镜表

- 数据在 **`data.rows`**，每行一镜，含两个字段：
  - **`imageGenerationPrompt`** —— 画面（喂图片生成）
  - **`videoMotionPrompt`** —— 运动（喂视频生成）
- 手改分镜表：`-u rows='[...]'`
- **`script` 与 `storyboard` 共用同一数据结构**，只是视图不同。

### 5.2 `libtv script storyboard <节点>` = 一键派生

```
前置：该节点已 --run 出分镜行
动作：建「分镜图组」→ 按行数派生等量 image 子节点 → 逐张 run 并轮询
```

⚠️ **未实跑**（会花钱）。
★ 这才是「故事板 → 套图 → 视频」的自动化链路 —— 比手工建 N 个 image 节点快得多。

### 5.3 官方示例里的手工版（旧模型时代）

`libtv-cli-skill\examples\pipes\group-and-node.md` 第 36–44 行有「三视图 + 服饰 + 汇总」的 NDJSON 管道写法。⚠️ 示例里写 `model=LibNano Pro` —— **现 26/18 个图片模型里都没这个名字**（`nebula-ultra` 的描述是「媲美 Nano pro 模型」）→ **示例写于旧模型时代，照抄必报错**。

---

## 6. 平台行为陷阱

1. ★ **后端会重写你的 prompt**（issue #12 实证，旧通道）：服务端把 message 改写后再发模型 —— 自动修拼写、**自动扩写**、**静默丢弃不认识的指令**（无报错）。⇒ **提示词精调可能被覆盖或吞掉，无 API 可关**。⚠️ CLI 通道是否同样重写**未验**。
2. **「不写」≠「没有」**：wan3.0 有声**默认开**，提示词不提台词/配乐模型会自己加 → 无声画面必须 `enableSound=off` **且**提示词写「无台词」「无背景音乐」。
3. **去水印实测未生效**：`download --without-ai-watermark` 两版产物**都带 `LibTV` 角标** → 大概率取决于会员等级。`--vip` 的实际价值在**码率（≈5.7×）** → 高码率版留给本地超分。
4. **`-s model=` 只认 modelName**（传 modelKey 报错）。★ **`nebula-ultra` 的 modelName = `Lib Navo Pro`** —— 官方示例写的 `LibNano Pro` 是**错拼**，照抄必报错。
5. ⚠️ **官方手册的模型样本采自 2026-04-14**（`node-types\README.md` 明写）→ 手册里的模型名容易过时，**以 `model search` 现场结果为准**。
6. ⚠️ **「真人参考图被硬拦」存疑**：记忆记载机制为 `properties.portrait` + `autoCompliance.enable`（`--run` 前校验上游图，过则转 `asset://<assetId>`，任一不过整体中止，`assetId` 由网页端人脸认证签发）。**但出片规范 §4.0 的代码级证据说 wan3.0 的 schema 无 `portrait` 字段、不进这条流程**。两者冲突，**待一次实测定论** —— 可能一方讲网页端、另一方讲 CLI 侧。

---

## 附：材料来源

| 来源 | 内容 | 取证日 |
|---|---|---|
| `getById?id=188` | 17 条 Slash + 4 分类 + 角色库维度 | 2026-09-23 |
| `getById?id=243` | 风格库 + 镜头库 | 2026-09-23 |
| `libtv image shortcut list` | CLI 实际可用的 16 条 | 2026-09-23 |
| `libtv model search --type image` | 18 个图片模型 | 2026-09-23 |
| MCP `search_models` / `get_model` | 26 个图片模型 / 单模型 schema 互证 | 2026-09-23 |
| `libtv-labs/libtv-skills` issues | 后端重写 prompt 等行为证据 | 2026-09-23 |
| 中间产物 | `.tmp\cfg188.json` · `.tmp\cfg243.json` · `.tmp\image_cap_export.md` | 可重生成 |
