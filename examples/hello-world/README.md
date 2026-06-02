# examples/hello-world

第一个跑通的端到端样例。本周（第 1-2 周）目标：

> 用户输入一句"写一篇关于 X 的公众号 + 小红书" → 用 `tools/run-pipeline` 跑通骨架版 → `db` 能查到产物。

## 跑通

```bash
# 0. 准备 db
cd ~/self-media-pipeline
rm -f library/data/smp.db*
sqlite3 library/data/smp.db < library/schema.sql

# 1. 生成 spec（写到一个固定文件，方便下游命令引用）
./tools/draft-spec \
    --topic "AI Agent 入门" \
    --platforms wechat,xiaohongshu \
    --word-count 800 \
    --source "https://lilianweng.github.io/posts/2023-06-23-agent/" \
    --out examples/hello-world/spec.json

# 2. 跑 pipeline（骨架版，不调 LLM）
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

本样例是**骨架版**，不调 LLM。真正生成内容需要等第 3 周：
- `render-html/tools/render.py`
- `render-image/tools/render.py`
- `platform-xiaohongshu/tools/slice_grid.py`
- writer subagent 用 LLM 起草

## 关联

- spec 生成器：`tools/draft-spec`
- pipeline runner：`tools/run-pipeline`
- library CLI：`tools/db`
