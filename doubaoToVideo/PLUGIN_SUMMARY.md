# DoubaoToVideo 插件已创建完成

## ✅ 已完成的工作

### 1. 目录结构
```
doubaoToVideo/
├── _assets/
│   └── icon.svg
├── provider/
│   ├── __init__.py
│   ├── doubao_ark.py
│   └── doubao_ark.yaml
├── tools/
│   ├── __init__.py
│   ├── text_to_video.py
│   ├── text_to_video.yaml
│   ├── image_to_video.py
│   └── image_to_video.yaml
├── api.md (豆包API文档)
├── manifest.yaml (插件元数据)
├── requirements.txt (依赖)
├── PRIVACY.md (隐私政策)
├── README.md (详细文档)
├── QUICKSTART.md (快速开始)
├── EXAMPLES.md (使用示例)
└── INSTALL.md (安装说明)
```

### 2. Provider 配置 (provider/doubao_ark.yaml)
- ✅ `ark_api_key` - 必填，API Key
- ✅ `base_url` - 可选，API 地址，默认 `https://ark.cn-beijing.volces.com`
- ✅ `model` - 可选，模型接入点，默认 `doubao-seedance-1-5-pro-251215`

### 3. 工具 1: Text to Video (文生视频)
**功能**: 纯文本提示词生成视频

**参数**:
- `prompt` - 必填，视频描述
- `generate_audio` - 可选，是否生成音频
- `ratio` - 可选，宽高比 (adaptive/16:9/9:16)
- `duration` - 可选，时长 (1-10秒)
- `watermark` - 可选，是否添加水印
- `poll_interval` - 可选，轮询间隔
- `max_polls` - 可选，最大轮询次数

### 4. 工具 2: Image to Video (图生视频)
**功能**: 参考图片 + 提示词生成视频

**参数**:
- `prompt` - 必填，视频描述，支持 `[图1]` 引用图片
- `reference_image` - 必填，单张参考图
- 支持本地文件上传
- 支持图片 URL
- 其他参数同 Text to Video

### 5. 核心功能
- ✅ 异步任务创建
- ✅ 自动轮询任务状态
- ✅ 任务成功后返回视频文件
- ✅ 本地文件自动转为 base64
- ✅ URL 图片直接使用
- ✅ 详细的任务信息返回
- ✅ 错误处理和提示

## 📦 使用方式

### 在 Dify 中导入
1. 进入 Dify 插件市场
2. 点击「创建插件」->「导入插件」
3. 选择 `doubaoToVideo` 目录
4. 配置 API Key、Base URL、Model
5. 启用插件

### 调用示例

#### 文生视频
```
工具: 豆包文生视频
参数:
  - 提示词: "一只可爱的猫咪在草地上玩耍"
  - 时长: 5
  - 生成音频: true
```

#### 图生视频
```
工具: 豆包图生视频
参数:
  - 参考图片: 上传1张图片
  - 提示词: "[图1]的角色开始跳舞"
  - 时长: 5
  - 生成音频: true
```

## 🔑 关键特性

1. **与 doubaotoImage 保持一致的配置**
   - 相同的 `api_key`、`base_url`、`model` 配置项
   - 一致的使用体验

2. **两种生成方式**
   - 文生视频: 纯文本提示
   - 图生视频: 参考图片 + 文本提示

3. **灵活的图片输入**
   - 本地上传 (自动转 base64)
   - URL 直接引用

4. **自动轮询**
   - 默认每 5 秒轮询一次
   - 最多轮询 120 次 (10 分钟)
   - 可自定义调整

5. **完整的返回信息**
   - 视频文件 (MP4)
   - 视频 URL
   - 任务详情 (分辨率、帧率、token 使用量等)

## 📚 文档说明

- `README.md` - 详细的功能说明和使用文档
- `QUICKSTART.md` - 快速开始指南
- `EXAMPLES.md` - 详细的使用示例
- `INSTALL.md` - 安装和配置说明
- `PRIVACY.md` - 隐私政策说明

## 🚀 下一步

1. 在 Dify 中导入插件
2. 配置豆包方舟的 API 凭据
3. 在工作流中使用「豆包文生视频」或「豆包图生视频」工具
4. 测试视频生成功能

## ⚠️ 注意事项

- 视频生成是异步过程，需要等待任务完成
- 提示词建议: 中文不超过 500 字，英文不超过 1000 词
- 参考图片要求: 格式为 jpeg/png/webp/bmp/tiff/gif，大小 < 30MB
- 视频时长范围: 1-10 秒
