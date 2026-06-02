# examples/hello-world

第一个跑通的端到端样例。目标：

> 用户输入一句"写一篇关于 X 的公众号 + 小红书" → 用 `tools/run-pipeline` 跑通工具层 pipeline → `db` 能查到产物。

## 跑通

```bash
# 0. 准备 db
cd ~/self-media-pipeline
./tools/db init

# 1. 生成 spec（写到一个固定文件，方便下游命令引用）
./tools/draft-spec \
    --topic "AI Agent 入门" \
    --platforms wechat,xiaohongshu \
    --word-count 800 \
    --source "https://lilianweng.github.io/posts/2023-06-23-agent/" \
    --out examples/hello-world/spec.json

# 2. 跑 pipeline（工具层真实渲染/适配/入库；writer/reviewer/fact-check 仍是 stub）
./tools/run-pipeline --spec examples/hello-world/spec.json

# 3. 查 library
./tools/db list-articles
./tools/db get 1
./tools/db search "Agent"
```

期望输出：

- `examples/hello-world/spec.json` 存在
- `./tools/db list-articles` 列出 1 条 article
- `./tools/db get 1` 列出 2 个 drafts（wechat + xiaohongshu）

## 局限性

本样例不调 LLM。当前真实执行的是：
- `render-html/tools/render.py`
- `render-image/tools/render.py`
- `render-image/tools/render_grid.py`
- `platform-wechat/tools/adapt_html.py`
- `platform-xiaohongshu/tools/adapt_html.py`
- `platform-xiaohongshu/tools/build_cards.py`
- SQLite/MCP 入库

仍是 stub 的部分：
- fact-check：只打印提示，不做自动核查
- writer：读取 `examples/hello-world/templates/draft-<platform>.json`
- reviewer：只跑平台硬约束脚本，不做 LLM 审校

## 关联

- spec 生成器：`tools/draft-spec`
- pipeline runner：`tools/run-pipeline`
- library CLI：`tools/db`
