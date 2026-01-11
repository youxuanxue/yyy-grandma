# yyy-grandma

针对银发经济（老年人群体）的怀旧影视剧短视频制作工具集。本项目包含视频下载、字幕提取、自动化剪辑（竖屏、双字幕）等全流程脚本。

## 目录结构

```
.
├── docs/                   # 文档 (提示词指南、市场分析等)
├── scripts/                # 通用工具脚本
│   ├── download.py         # 视频下载 (基于 yt-dlp)
│   ├── extract_subs.py     # 字幕提取 (基于 OpenAI Whisper)
│   └── produce_short_video.py # 自动化剪辑与合成
└── series/                 # 电视剧项目数据
    └── jinhun/             # 示例：《金婚》
        ├── config/         # 剪辑策略文件 (*.json)
        ├── downloads/      # 视频源文件与字幕
        └── output/         # 生成的短视频成品
```

## 环境准备

本项目使用 `uv` 进行包管理。

```bash
# 初始化环境 (如果需要)
uv sync
```

确保系统已安装 `ffmpeg`。

## 使用流程

以制作《金婚》为例：

### 1. 下载视频

下载视频到指定系列的 downloads 目录：

```bash
# 用法: uv run scripts/download.py <视频URL> <输出目录>
uv run scripts/download.py "https://youtube.com/..." series/jinhun/downloads
```

### 2. 提取字幕

自动提取视频字幕（SRT格式）：

```bash
# 用法: uv run scripts/extract_subs.py <视频文件或目录>
# 默认会按照文件名顺序(01, 02...)处理
uv run scripts/extract_subs.py series/jinhun/downloads
```

### 3. 制定剪辑策略

参考 `docs/prompt_generation_guide.md`，使用 AI 辅助生成剪辑策略 JSON 文件，并保存到 `series/jinhun/config/` 目录。
命名规范：`《剧名》第XX集-Strategy.json`

### 4. 生成短视频

执行自动化剪辑脚本，生成 9:16 竖屏短视频：

```bash
# 用法: uv run scripts/produce_short_video.py <策略JSON路径>
uv run scripts/produce_short_video.py series/jinhun/config/《金婚》第01集-Strategy.json
```

输出文件将保存在 `series/jinhun/output/` 目录。

## 脚本说明

- **produce_short_video.py**: 核心脚本。读取 JSON 策略，利用 FFmpeg 自动截取片段、转竖屏、添加高斯模糊背景、添加顶部标题和底部解说字幕，最后合并为一个完整的短视频。
- **extract_subs.py**: 使用 Whisper 模型提取字幕，支持批量处理。
