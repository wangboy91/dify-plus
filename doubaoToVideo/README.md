# Doubao Ark Video Plugin

豆包方舟视频生成插件，支持文生视频和图生视频两种方式。

## 功能特性

- **文本生成视频**：通过输入提示词直接生成视频
- **参考图生成视频**：支持上传本地图片或使用图片URL，结合提示词生成视频
- **异步任务处理**：自动创建任务并轮询任务状态，直到视频生成完成
- **文件下载**：自动生成的视频可直接下载

## 配置参数

### Provider 配置

- **ark_api_key** (必需): 豆包方舟 API Key
- **base_url** (可选): API 基础地址，默认 `https://ark.cn-beijing.volces.com`
- **model（接入点）** (可选): 模型接入点，默认 `doubao-seedance-1-5-pro-251215`

## 工具说明

### 1. Text to Video (文生视频)

根据文本提示词生成视频。

**参数**:
- `prompt` (必需): 视频生成的提示词描述
- `generate_audio` (可选): 是否生成音频，默认 `true`
- `ratio` (可选): 视频宽高比，默认 `adaptive` (可选: `adaptive`, `16:9`, `9:16`)
- `duration` (可选): 视频时长（秒），默认 `5`，范围 1-10
- `watermark` (可选): 是否添加水印，默认 `false`
- `poll_interval` (可选): 轮询间隔（秒），默认 `5`
- `max_polls` (可选): 最大轮询次数，默认 `120`

### 2. Image to Video (参考图+提示词生视频)

根据单张参考图和提示词生成视频。

**参数**:
- `prompt` (必需): 视频生成的提示词描述，可以使用 `[图1]` 引用参考图
- `reference_image` (可选): 单张参考图文件输入
  - 本地上传图片
  - 直接粘贴图片 URL
- `generate_audio` (可选): 是否生成音频，默认 `true`
- `ratio` (可选): 视频宽高比，默认 `adaptive` (可选: `adaptive`, `16:9`, `9:16`)
- `duration` (可选): 视频时长（秒），默认 `5`，范围 1-10
- `watermark` (可选): 是否添加水印，默认 `false`
- `poll_interval` (可选): 轮询间隔（秒），默认 `5`
- `max_polls` (可选): 最大轮询次数，默认 `120`

## 使用说明

### 文生视频示例

```
提示词: "女孩抱着狐狸，女孩睁开眼，温柔地看向镜头，狐狸友善地抱着，镜头缓缓拉出，女孩的头发被风吹动，可以听到风声"

参数配置:
- 生成音频: 是
- 宽高比: 自适应
- 时长: 5秒
```

### 图生视频示例

```
参考图片: 上传1张参考图片（本地文件或URL）
提示词: "[图1]中的角色在草坪上行走，3D卡通风格"

参数配置:
- 生成音频: 是
- 宽高比: 16:9
- 时长: 5秒
```

## 技术实现

- 使用豆包方舟 API `POST /contents/generations/tasks` 创建视频生成任务
- 通过 `GET /contents/generations/tasks/{id}` 轮询任务状态
- 任务成功后获取视频下载链接并返回

## 工作流变量绑定建议

- `prompt`：直接绑定上游文本变量。
- `reference_image`：绑定上游文件变量（图片类型）。

## 注意事项

1. 参考图片要求：
   - 格式：jpeg、png、webp、bmp、tiff、gif（Seedance 1.5 pro 新增支持 heic 和 heif）
   - 宽高比（宽/高）：(0.4, 2.5)
   - 宽高长度（px）：(300, 6000)
   - 大小：小于 30 MB

2. 提示词建议：
   - 中文不超过 500 字
   - 英文不超过 1000 词
   - 字数过多信息容易分散，模型可能因此忽略细节

3. 任务超时：
   - 如果视频生成时间过长，可以调整 `poll_interval` 和 `max_polls` 参数
   - 默认最多轮询 120 次，每次间隔 5 秒（总计 10 分钟）

## 依赖

- Python 3.12
- requests

## 本地测试
```bash
pyenv local 3.12.9
python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## 打包导入 Dify
```bash
# 在插件目录的上一层执行
dify plugin package ./doubaoToVideo

```
在 Dify 后台插件管理页上传 并启用。
