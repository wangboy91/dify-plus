# Doubao Ark Image (Dify Tool Plugin)

这是一个 Dify `tool` 类型插件，用于调用豆包方舟（Seedream）文生图接口生成图片。

## 功能
- 文生图（单图/组图）
- 支持在工作流中通过 `prompt` 使用上下文变量
- 配置项支持 `ARK_API_KEY`、`Base URL`、`Model`

## 配置项（Provider）
- `ARK_API_KEY`（必填）
- `Base URL`（默认 `https://ark.cn-beijing.volces.com`）
- `Model`（默认 `ep-20260125201054-pfrb4`）

## 工具参数（Tool）
- `prompt`（必填，支持工作流上下文变量）
- `size`（默认 `4K`）
- `sequential_image_generation`（可选：`disabled` / `auto`）
- `max_images`（可选，仅在 `auto` 时生效）
- `response_format`（可选：`url` / `b64_json`）
- `watermark`（可选，默认 `true`）

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
dify plugin package ./doubaotoImage

```
在 Dify 后台插件管理页上传 并启用。

## 隐私说明
插件会将 `prompt` 与生成参数发送到配置的豆包方舟接口，不会在插件侧存储用户数据或生成结果。

## 目录结构
```
.
├─ _assets
│  └─ icon.svg
├─ provider
│  ├─ __init__.py
│  ├─ doubao_ark.py
│  └─ doubao_ark.yaml
├─ tools
│  ├─ __init__.py
│  ├─ text_to_image.py
│  └─ text_to_image.yaml
├─ api.md
├─ main.py
├─ manifest.yaml
├─ PRIVACY.md
├─ README.md
└─ requirements.txt
```
