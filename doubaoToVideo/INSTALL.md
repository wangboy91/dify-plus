# 安装说明

## Dify 中安装插件

### 方式一：本地文件导入

1. 在 Dify 的插件页面点击「创建插件」
2. 选择「导入插件」
3. 选择 `doubaoToVideo` 目录
4. 点击「导入」

### 方式二：ZIP 压缩包导入

1. 压缩插件目录：
   ```bash
   cd /Users/wangboy/MyWork/dify-plus
   zip -r doubaoToVideo.zip doubaoToVideo -x "*.DS_Store" -x "*/.DS_Store"
   ```

2. 在 Dify 中上传 ZIP 文件

### 方式三：Git 仓库导入

如果你将插件推送到 Git 仓库：
1. 在 Dify 中选择「从 Git 仓库导入」
2. 输入仓库地址和分支

## 配置插件

导入成功后，进入插件配置页面：

1. **配置 Provider 凭据**：
   - `ARK API Key`: 你的豆包方舟 API Key
   - `Base URL`: `https://ark.cn-beijing.volces.com` (可选，默认值)
   - `Model`: 模型接入点（可选），例如 `doubao-seedance-1-5-pro-251215`

2. **保存配置**

3. **启用插件**

## 验证安装

配置完成后，你可以：

1. 在工作流中添加「豆包文生视频」或「豆包图生视频」工具
2. 测试生成一个简单的视频
3. 检查返回结果是否包含视频文件

## 依赖安装

插件依赖会自动安装，主要依赖：
- `requests` - HTTP 请求库

如需手动安装依赖：
```bash
cd /Users/wangboy/MyWork/dify-plus/doubaoToVideo
pip install -r requirements.txt
```

## 故障排查

### 问题 1: 导入失败
- 检查 YAML 文件格式是否正确
- 确保所有必需文件都存在

### 问题 2: 配置保存失败
- 检查 API Key 是否正确
- 确认网络连接正常

### 问题 3: 视频生成失败
- 检查 API Key 权限
- 查看返回的错误信息
- 检查提示词格式和长度

## 更新插件

如需更新插件：

1. 修改相关文件
2. 在 Dify 中重新导入插件
3. 重新配置凭据 (如果配置格式有变化)

## 卸载插件

在 Dify 插件管理页面：
1. 找到「豆包方舟视频生成」插件
2. 点击「删除」
3. 确认删除
