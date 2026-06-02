---
name: media-provider
description: 多媒体生成 provider 抽象层。用于图片、音频、视频生成；当前可适配 MiniMax CLI，但 workflow 不直接耦合任何厂商 CLI。
---

# media-provider

## 目标

把图片、音频、视频生成能力从 self-media pipeline 中解耦出来。pipeline 只提交标准化请求，provider adapter 决定是否调用 MiniMax CLI、其他模型 CLI、云 API 或本地工具。

## Provider Contract

请求统一写成 JSON：

```json
{
  "kind": "image | audio | video",
  "provider": "minimax | other | auto",
  "prompt": "生成内容描述",
  "output_dir": "examples/<run-id>/media/",
  "spec": {
    "width_px": 1080,
    "height_px": 1440,
    "duration_sec": 8,
    "voice": "optional"
  },
  "metadata": {
    "platform": "xiaohongshu",
    "slot": "cover"
  }
}
```

响应统一写成 JSON：

```json
{
  "provider": "minimax",
  "kind": "image",
  "status": "success",
  "artifacts": [
    {
      "path": "examples/<run-id>/media/cover.png",
      "mime": "image/png",
      "width_px": 1080,
      "height_px": 1440,
      "size_bytes": 123456
    }
  ],
  "warnings": []
}
```

## MiniMax CLI 适配原则

- MiniMax CLI 只能出现在 provider adapter 内部，不能散落在 writer/reviewer/renderer/pipeline。
- 所有 provider 调用都必须产出 artifact manifest，供 library 入库。
- provider 失败时返回结构化错误；上游可以降级为 CSS/SVG/占位图，不直接崩溃整条内容 pipeline。
- 后续切换其他 CLI 时，只替换 adapter，不改平台 skill 和内容库 schema。

