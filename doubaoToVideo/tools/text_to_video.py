from typing import Generator
import time
import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class TextToVideoTool(Tool):
    def _invoke(self, tool_parameters: dict) -> Generator[ToolInvokeMessage, None, None]:
        credentials = self.runtime.credentials or {}
        api_key = credentials.get("ark_api_key")
        base_url = credentials.get("base_url") or "https://ark.cn-beijing.volces.com"
        model = tool_parameters.get("model") or "doubao-seedance-1-5-pro-251215"

        prompt = tool_parameters.get("prompt")
        if not prompt:
            yield self.create_text_message("prompt is required")
            return

        generate_audio = tool_parameters.get("generate_audio", True)
        ratio = tool_parameters.get("ratio", "adaptive")
        duration = tool_parameters.get("duration", 5)
        watermark = tool_parameters.get("watermark", False)
        poll_interval = tool_parameters.get("poll_interval", 5)
        max_polls = tool_parameters.get("max_polls", 120)

        payload = {
            "model": model,
            "content": [
                {
                    "type": "text",
                    "text": prompt
                }
            ],
            "generate_audio": generate_audio,
            "ratio": ratio,
            "duration": duration,
            "watermark": watermark
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url.rstrip('/')}/api/v3/contents/generations/tasks"

        # Step 1: 创建视频生成任务
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            task_id = data.get("id")
            if not task_id:
                yield self.create_text_message("Failed to create video generation task")
                return

            yield self.create_text_message(f"Task created successfully, task ID: {task_id}")

            # Step 2: 轮询查询任务状态
            poll_count = 0
            while poll_count < max_polls:
                poll_count += 1
                task_url = f"{url}/{task_id}"

                try:
                    task_response = requests.get(task_url, headers=headers, timeout=10)
                    task_response.raise_for_status()
                    task_data = task_response.json()

                    status = task_data.get("status")
                    yield self.create_text_message(f"Poll {poll_count}/{max_polls}: Task status is {status}")

                    if status == "succeeded":
                        video_url = task_data.get("content", {}).get("video_url")
                        if video_url:
                            yield self.create_text_message(f"Video generation completed!")
                            yield self.create_text_message(f"Download URL: {video_url}")

                            # 尝试下载视频文件
                            try:
                                video_resp = requests.get(video_url, timeout=30)
                                if video_resp.status_code == 200:
                                    yield self.create_file(
                                        data=video_resp.content,
                                        filename="generated_video.mp4",
                                        mime_type="video/mp4"
                                    )
                            except Exception as e:
                                yield self.create_text_message(f"Note: Could not download video directly: {str(e)}")

                            # 返回详细信息
                            yield self.create_json_message({
                                "task_id": task_id,
                                "model": task_data.get("model"),
                                "status": status,
                                "video_url": video_url,
                                "resolution": task_data.get("resolution"),
                                "ratio": task_data.get("ratio"),
                                "duration": task_data.get("duration"),
                                "framespersecond": task_data.get("framespersecond"),
                                "seed": task_data.get("seed"),
                                "usage": task_data.get("usage"),
                                "created_at": task_data.get("created_at"),
                                "updated_at": task_data.get("updated_at")
                            })
                        else:
                            yield self.create_text_message("Task succeeded but no video URL found")
                        return

                    elif status == "failed":
                        error_msg = task_data.get("error", {}).get("message", "Unknown error")
                        yield self.create_text_message(f"Task failed: {error_msg}")
                        yield self.create_json_message(task_data)
                        return

                    elif status in ["queued", "running"]:
                        # 继续轮询
                        time.sleep(poll_interval)
                        continue

                except requests.exceptions.RequestException as e:
                    yield self.create_text_message(f"Error polling task status: {str(e)}")
                    time.sleep(poll_interval)

            yield self.create_text_message(f"Task did not complete after {max_polls} polls. Status: {status}")

        except requests.exceptions.RequestException as e:
            yield self.create_text_message(f"Error creating video generation task: {str(e)}")
