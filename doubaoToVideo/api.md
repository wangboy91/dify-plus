
视频生成是一个异步过程：
成功调用 POST /contents/generations/tasks 接口后，API 将返回一个任务 ID 。
您可以轮询 GET /contents/generations/tasks/{id} 接口，直到任务状态变为 succeeded；或者使用 Webhook 自动接收视频生成任务的状态变化。
任务完成后，您可在 content.video_url 字段处，下载最终生成的 MP4 文件。


Step1: 创建视频生成任务
通过 POST /contents/generations/tasks 创建视频生成任务。

curl https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seedance-1-5-pro-251215",
    "content": [
        {
            "type": "text",
            "text": "女孩抱着狐狸，女孩睁开眼，温柔地看向镜头，狐狸友善地抱着，镜头缓缓拉出，女孩的头发被风吹动，可以听到风声"
        },
        {
            "type": "image_url",
            "image_url": {
                "url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/i2v_foxrgirl.png"
            }
        }
    ],
    "generate_audio": true,
    "ratio": "adaptive",
    "duration": 5,
    "watermark": false
}'

content object[]  
输入给模型，生成视频的信息，支持文本、图片和视频（样片，Draft 视频）格式。支持以下几种组合：
文本

content.type string  
输入内容的类型，此处应为 text。

content.text string  
输入给模型的文本提示词，描述期望生成的视频。
支持中英文。建议中文不超过500字，英文不超过1000词。字数过多信息容易分散，模型可能因此忽略细节，只关注重点，造成视频缺失部分元素

文本+图片
属性

content.type string  
输入内容的类型，此处应为 image_url。支持图片URL或图片 Base64 编码。

content.image_url object  
输入给模型的图片对象。
 
content.image_url.url string  
图片信息，可以是图片URL或图片 Base64 编码。
图片URL：请确保图片URL可被访问。
Base64编码：请遵循此格式data:image/<图片格式>;base64,<Base64编码>，注意 <图片格式> 需小写，如 data:image/png;base64,{base64_image}。
说明
传入图片需要满足以下条件：
图片格式：jpeg、png、webp、bmp、tiff、gif。其中，Seedance 1.5 pro 新增支持 heic 和 heif。
宽高比（宽/高）： (0.4, 2.5) 
宽高长度（px）：(300, 6000)
大小：小于 30 MB

content.role string 条件必填
图片的位置或用途。
注意
首帧图生视频、首尾帧图生视频、参考图生视频为 3 种互斥的场景，不支持混用。
图生视频-首帧
支持模型：所有图生视频模型
字段role取值：需要传入1个image_url对象，且字段role可不填，或字段role为：first_frame

图生视频-首尾帧
支持模型：Seedance 1.5 pro、Seedance 1.0 pro、Seedance 1.0 lite i2v 
字段role取值：需要传入2个image_url对象，且字段role必填。
首帧图片对应的字段role为：first_frame
尾帧图片对应的字段role为：last_frame
图生视频-参考图
支持模型：Seedance 1.0 lite i2v
字段role取值：需要传入1～4个image_url对象，且字段role必填。
每张参考图片对应的字段role均为：reference_image

说明
参考图生视频功能的文本提示词，可以用自然语言指定多张图片的组合。但若想有更好的指令遵循效果，推荐使用“[图1]xxx，[图2]xxx”的方式来指定图片。
示例1：戴着眼镜穿着蓝色T恤的男生和柯基小狗，坐在草坪上，3D卡通风格
示例2：[图1]戴着眼镜穿着蓝色T恤的男生和[图2]的柯基小狗，坐在[图3]的草坪上，3D卡通风格

视频：其中视频指已成功生成的样片视频，模型可基于样片生成高质量正式视频。
content.type string  
输入内容的类型，此处应为 draft_task。

content.draft_task object  
输入给模型的样片任务。

content.draft_task.id string  
样片任务 ID。平台将自动复用 Draft 视频使用的用户输入（model、content.text、content.image_url、generate_audio、seed、ratio、duration、camera_fixed ），生成正式视频。其余参数支持指定，不指定将使用本模型的默认值。
使用分为两步：Step1: 调用本接口生成 Draft 视频。Step2: 如果确认 Draft 视频符合预期，可基于 Step1 返回的 Draft 视频任务 ID，调用本接口生成最终视频


请求成功后，系统将返回一个任务 ID。

{
  "id": "cgt-2025******-****"
}
Step2: 查询视频生成任务
利用创建视频生成任务时返回的 ID ，您可以查询视频生成任务的详细状态与结果。此接口会返回任务的当前状态（如 queued 、running 、 succeeded 等）以及生成的视频相关信息（如视频下载链接、分辨率、时长等）。

# Replace cgt-2025**** with the ID acquired from "Create Video Generation Task".

curl -X GET https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/cgt-2025**** \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY"

  当任务状态变为 succeeded 后，您可在 content.video_url 字段处，下载最终生成的视频文件
{
  "id": "cgt-2025******-****",
  "model": "doubao-seedance-1-5-pro-251215",
  "status": "succeeded",
  "content": {
    "video_url": "https://ark-content-generation-cn-beijing.tos-cn-beijing.volces.com/xxx"
  },
  "usage": {
    "completion_tokens": 108900,
    "total_tokens": 108900
  },
  "created_at": 1743414619,
  "updated_at": 1743414673,
  "seed": 10,
  "resolution": "720p",
  "ratio": "16:9",
  "duration": 5,
  "framespersecond": 24,
  "service_tier":"default",
  "execution_expires_after":172800,
  "generate_audio":true,
  "draft":false
}