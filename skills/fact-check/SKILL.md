---
name: fact-check
description: 内容审校：事实核查、敏感词扫描、版权风险、风格一致性。给 reviewer subagent 用。 本 skill **不**做"硬性合规审查"（那是法务/合规团队的活），只做"内容生产时的快速自检"。
---

# fact-check —— 内容审校

## 这个 skill 干什么

对 writer 的 draft 做 4 类自检：

1. **事实核查**：声明、数字、引用是否与原料一致
2. **敏感词扫描**：是否含政治、医疗、金融、版权高风险词
3. **版权风险**：是否复制了他人的原创表述（不查全网相似度，只查显式引用）
4. **风格一致性**：与 `style_reference` 的语气、结构、术语是否对齐

## 这个 skill 不干什么

- 不查全网相似度（不接查重服务）
- 不做法律意见（仅给风险提示）
- 不删改内容——只**报告**问题，由 writer 改

## 报告契约

```json
{
  "pass": true | false,
  "issues": [
    {
      "type": "facts | sensitive_words | copyright | style",
      "severity": "block | warn | info",
      "location": "<摘录或位置>",
      "message": "<给 writer 的修改建议>",
      "source": "<如果是事实核查，附 source URL>"
    }
  ],
  "summary": {
    "block_count": 0,
    "warn_count": 0,
    "info_count": 0
  }
}
```

**严重度**：
- `block`：必须修改才能过审
- `warn`：建议修改
- `info`：备注，不阻塞

## 工作流

### 1. 事实核查

如果 `source_material` 是 URL：
- 调 `web_extract` 抓原料原文
- 把 draft 的**关键声明**（数字、人物、事件、日期）逐条跟原文对
- 偏差 > 0 标 `block`

如果 `source_material` 是用户自写：
- 跳过事实核查（信任用户）
- 在报告里写 `info: "user-supplied source, not verified"`

### 2. 敏感词扫描

工具：`tools/scan_words.py`

```bash
python skills/fact-check/tools/scan_words.py draft.md
```

词表：`tools/wordlists/sensitive.txt`（**第 5 周实现**——本周先放示例词）

返回命中列表 + 上下文 + 风险等级。

### 3. 版权风险

- 显式引用：检查是否标了出处（"<引用>" — 出自 X）
- 大段复制：检测连续超过 100 字且未标出处的段落
- 工具：`tools/check_copyright.py`（**第 5 周实现**）

### 4. 风格一致性

如果给了 `style_reference`：
- 提取 reference 的：句长分布、emoji 频率、术语表、段落结构
- 跟 draft 对比
- 偏差 > 30% 标 `warn`

工具：`tools/check_style.py`（**第 5 周实现**）

## 工具

| 工具 | 实现周 | 说明 |
|---|---|---|
| `tools/scan_words.py` | 第 5 周 | 敏感词扫描 |
| `tools/check_copyright.py` | 第 5 周 | 显式引用 + 大段复制检测 |
| `tools/check_style.py` | 第 5 周 | 风格一致性（基础句长 + 词频） |

**第 1-2 周**：本 skill 只做"事实核查"（用 web_extract），其他三项先做空 stub。

## 关联

- 上游：被 self-media-pipeline 的 reviewer subagent 加载
- 下游：审校结果回 writer 修改
