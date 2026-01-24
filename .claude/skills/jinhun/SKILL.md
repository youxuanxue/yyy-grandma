---
name: jinhun
description: 金婚短视频制作工作流 - 分析剧本、生成策略、渲染视频、发布到平台
---

# /jinhun - 金婚短视频制作工作流

根据子命令执行不同操作。

## 参数格式

$ARGUMENTS = <子命令> <集数> [平台]

子命令：
- `analyze`: 分析字幕，生成策略 JSON
- `render`: 读取策略 JSON，生成视频
- `publish`: 发布视频到指定平台
- `full`: 完整流程（分析 + 生成，跳过人工审核）

集数：两位数字，如 01, 07, 12

平台（仅 publish 命令需要）：
- `wechat`: 微信视频号
- `youtube`: YouTube Shorts
- `both`: 同时发布到两个平台（默认）

## 工作流程

### 当子命令为 `analyze` 时：

1. 读取 `docs/jinhun_script_prompt.md` 获取分析规范
2. 读取字幕文件 `series/jinhun/downloads/jinhun{集数}.srt`
3. 按照规范分析剧情，筛选 3-5 个高光片段
4. 生成策略 JSON 文件到 `series/jinhun/config/jinhun{集数}-Strategy.json`
5. 输出摘要，提示用户检查并修改 JSON 后运行 `/jinhun render {集数}`

### 当子命令为 `render` 时：

1. 确认策略文件存在：`series/jinhun/config/jinhun{集数}-Strategy.json`
2. 删除临时目录（确保干净状态）：
   ```bash
   rm -rf series/jinhun/temp_clips
   ```
3. 运行视频生成脚本：
   ```bash
   uv run scripts/produce_short_video.py series/jinhun/config/jinhun{集数}-Strategy.json
   ```
4. 输出结果路径

### 当子命令为 `publish` 时：

1. 确认视频文件存在：`series/jinhun/output/jinhun{集数}-Clip.mp4`
2. 确认策略文件存在：`series/jinhun/config/jinhun{集数}-Strategy.json`
3. 从策略 JSON 中提取发布信息，生成临时发布脚本：
   - 读取策略 JSON 中的 `wechat` 和 `youtube` 字段
   - 生成临时文件 `series/jinhun/temp_publish.json`
4. 调用 media-publisher 发布：
   ```bash
   cd /Users/xuejiao/Codes/yyy_monkey/media-publisher && \
   uv run media-publisher \
     --video /Users/xuejiao/Codes/yyy-grandma/series/jinhun/output/jinhun{集数}-Clip.mp4 \
     --platform {平台} \
     --script /Users/xuejiao/Codes/yyy-grandma/series/jinhun/temp_publish.json
   ```
5. 删除临时发布脚本
6. 输出发布结果

**注意事项：**
- 微信视频号：发布过程中会打开浏览器，需要手动点击「发布」按钮
- YouTube：首次使用需要完成 OAuth2 授权，需要科学上网
- 如需设置 YouTube 隐私级别，可在策略 JSON 的 `youtube.privacy` 中指定（默认 private）

### 当子命令为 `full` 时：

依次执行 analyze 和 render，中间不暂停。（不包含 publish，需单独执行）

## 示例

```bash
/jinhun analyze 07         # 分析第7集，生成策略 JSON
/jinhun render 07          # 渲染第7集视频
/jinhun publish 07         # 发布第7集到所有平台（wechat + youtube）
/jinhun publish 07 wechat  # 仅发布到微信视频号
/jinhun publish 07 youtube # 仅发布到 YouTube Shorts
/jinhun full 07            # 完整流程（分析 + 渲染）
```

## 输出文件

- 策略 JSON: `series/jinhun/config/jinhun{XX}-Strategy.json`
- 视频文件: `series/jinhun/output/jinhun{XX}-Clip.mp4`

## 策略 JSON 发布字段格式

策略 JSON 中需包含以下发布信息：

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

## 依赖项目

- **media-publisher**: `/Users/xuejiao/Codes/yyy_monkey/media-publisher`
  - 用于视频发布到微信视频号和 YouTube
  - 首次使用需配置 YouTube OAuth2 凭据
