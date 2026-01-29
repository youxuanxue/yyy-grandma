---
name: jinhun
description: 金婚短视频制作工作流 - 分析字幕生成策略 JSON、渲染视频、发布到微信视频号或 YouTube。当用户提到金婚、jinhun、短视频制作、视频发布时使用此 skill。
---

# 金婚短视频制作工作流

根据子命令执行不同操作。

## 参数格式

`$ARGUMENTS = <子命令> <集数> [平台]`

**子命令：**
- `analyze`: 分析字幕，生成策略 JSON
- `render`: 读取策略 JSON，生成视频
- `publish`: 发布视频到指定平台
- `full`: 完整流程（分析 + 渲染，跳过人工审核）

**集数：** 两位数字，如 01, 07, 12

**平台（仅 publish 命令需要）：**
- `wechat`: 微信视频号
- `youtube`: YouTube Shorts
- `both`: 同时发布（默认）

## 工作流程

### analyze 子命令

1. 读取 `docs/jinhun_script_prompt.md` 获取分析规范
2. 读取字幕文件 `series/jinhun/downloads/jinhun{集数}.srt`
3. 按规范分析剧情，生成策略 JSON 到 `series/jinhun/config/jinhun{集数}-Strategy.json`
4. 输出摘要，提示用户检查后运行 render

### render 子命令

1. 确认策略文件存在
2. 清理临时目录：

```bash
rm -rf series/jinhun/temp_clips
```

3. 运行视频生成：

```bash
uv run scripts/produce_short_video.py series/jinhun/config/jinhun{集数}-Strategy.json
```

4. 输出结果路径

### publish 子命令

1. 确认视频和策略文件存在
2. 从策略 JSON 提取 `wechat`/`youtube` 字段，生成临时文件 `series/jinhun/temp_publish.json`
3. 调用 media-publisher：

```bash
cd /Users/xuejiao/Codes/yyy_monkey/media-publisher && \
uv run media-publisher \
  --video /Users/xuejiao/Codes/yyy-grandma/series/jinhun/output/jinhun{集数}-Clip.mp4 \
  --platform {平台} \
  --script /Users/xuejiao/Codes/yyy-grandma/series/jinhun/temp_publish.json
```

4. 删除临时文件，输出结果

**注意：**
- 微信：需手动点击「发布」按钮
- YouTube：首次需 OAuth2 授权，需科学上网

### full 子命令

依次执行 analyze → render（不含 publish）

## 示例

```bash
/jinhun analyze 07         # 分析第7集
/jinhun render 07          # 渲染第7集
/jinhun publish 07         # 发布到所有平台
/jinhun publish 07 wechat  # 仅发布微信
/jinhun full 07            # 完整流程
```

## 输出文件

- 策略 JSON: `series/jinhun/config/jinhun{XX}-Strategy.json`
- 视频文件: `series/jinhun/output/jinhun{XX}-Clip.mp4`

## 策略 JSON 发布字段

```json
{
  "wechat": {
    "title": "视频标题（最多16字）",
    "description": "视频描述",
    "hashtags": ["#标签1", "#标签2"],
    "heji": "合集名称（可选）",
    "huodong": "活动名称（可选）"
  },
  "youtube": {
    "title": "YouTube 视频标题",
    "description": "YouTube 视频描述",
    "tags": ["标签1", "标签2"],
    "playlists": "播放列表名称（可选）",
    "privacy": "private"
  }
}
```

## 依赖

- **media-publisher**: `/Users/xuejiao/Codes/yyy_monkey/media-publisher`
  - 首次使用需配置 YouTube OAuth2 凭据
