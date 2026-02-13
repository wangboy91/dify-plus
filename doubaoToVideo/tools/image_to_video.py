import base64
import time
from typing import Generator, Optional
from urllib.parse import urlparse

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class ImageToVideoTool(Tool):
    def _invoke(self, tool_parameters: dict) -> Generator[ToolInvokeMessage, None, None]:
        credentials = self.runtime.credentials or {}
        api_key = credentials.get("ark_api_key")
        base_url = credentials.get("base_url") or "https://ark.cn-beijing.volces.com"
        model = credentials.get("model") or "doubao-seedance-1-5-pro-251215"

        prompt = tool_parameters.get("prompt")
        if not prompt:
            yield self.create_text_message("prompt is required")
            return

        image_url = self._resolve_reference_image_url(tool_parameters)
        if not image_url:
            yield self.create_text_message("reference_image is required")
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
                    "text": prompt,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                    },
                    "role": "reference_image",
                },
            ],
            "generate_audio": generate_audio,
            "ratio": ratio,
            "duration": duration,
            "watermark": watermark,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url.rstrip('/')}/api/v3/contents/generations/tasks"

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            task_id = data.get("id")
            if not task_id:
                yield self.create_text_message("Failed to create video generation task")
                return

            yield self.create_text_message(f"Task created successfully, task ID: {task_id}")

            poll_count = 0
            status = "queued"
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
                            yield self.create_text_message("Video generation completed!")
                            yield self.create_text_message(f"Download URL: {video_url}")

                            try:
                                video_resp = requests.get(video_url, timeout=30)
                                if video_resp.status_code == 200:
                                    yield self.create_file_message(
                                        file=video_resp.content,
                                        filename="generated_video.mp4",
                                        mime_type="video/mp4",
                                    )
                            except Exception as error:
                                yield self.create_text_message(
                                    f"Note: Could not download video directly: {str(error)}"
                                )

                            yield self.create_json_message(
                                {
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
                                    "updated_at": task_data.get("updated_at"),
                                }
                            )
                        else:
                            yield self.create_text_message("Task succeeded but no video URL found")
                        return

                    if status == "failed":
                        error_msg = task_data.get("error", {}).get("message", "Unknown error")
                        yield self.create_text_message(f"Task failed: {error_msg}")
                        yield self.create_json_message(task_data)
                        return

                    if status in ["queued", "running"]:
                        time.sleep(poll_interval)
                        continue

                except requests.exceptions.RequestException as error:
                    yield self.create_text_message(f"Error polling task status: {str(error)}")
                    time.sleep(poll_interval)

            yield self.create_text_message(
                f"Task did not complete after {max_polls} polls. Status: {status}"
            )

        except requests.exceptions.RequestException as error:
            yield self.create_text_message(f"Error creating video generation task: {str(error)}")

    def _resolve_reference_image_url(self, tool_parameters: dict) -> Optional[str]:
        image_url_input = tool_parameters.get("reference_image_url")
        if isinstance(image_url_input, str) and image_url_input.strip():
            normalized = image_url_input.strip()
            if self._looks_like_url_or_data_uri(normalized):
                return normalized
            return self._file_id_to_data_uri(normalized)

        reference_image = tool_parameters.get("reference_image")
        if isinstance(reference_image, str) and reference_image.strip():
            normalized = reference_image.strip()
            if self._looks_like_url_or_data_uri(normalized):
                return normalized
            return self._file_id_to_data_uri(normalized)
        if isinstance(reference_image, dict):
            return self._extract_image_url(reference_image)

        # Backward-compatible fallback for previous array-based parameter.
        legacy_images = tool_parameters.get("reference_images")
        if isinstance(legacy_images, list) and legacy_images:
            first = legacy_images[0]
            if isinstance(first, dict):
                return self._extract_image_url(first)
            if isinstance(first, str) and first.strip():
                return first.strip()

        return None

    def _extract_image_url(self, image_input: dict) -> Optional[str]:
        transfer_method = image_input.get("transfer_method")

        if transfer_method == "remote_url":
            return image_input.get("url")

        if transfer_method == "local_file":
            file_id = self._extract_file_id(image_input)
            return self._file_id_to_data_uri(file_id)

        # Support upstream variable mapping where transfer_method might be absent.
        url_value = image_input.get("url")
        if isinstance(url_value, str) and self._looks_like_url_or_data_uri(url_value):
            return url_value.strip()

        nested_value = image_input.get("value")
        if isinstance(nested_value, dict):
            nested_url = self._extract_image_url(nested_value)
            if nested_url:
                return nested_url

        file_id = self._extract_file_id(image_input)
        if file_id:
            return self._file_id_to_data_uri(file_id)

        return None

    def _extract_file_id(self, data: dict) -> Optional[str]:
        # Dify file variables may expose different id fields depending on node/runtime.
        for key in ["id", "related_id", "file_id", "upload_file_id"]:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _file_id_to_data_uri(self, file_id: Optional[str]) -> Optional[str]:
        if not file_id or not self.runtime.file_manager:
            return None

        upload_file = self.runtime.file_manager.get(file_id)
        if not upload_file:
            return None

        file_content = upload_file.read()
        mime_type = self._normalize_image_mime_type(upload_file.mime_type)
        return f"data:{mime_type};base64,{base64.b64encode(file_content).decode('utf-8')}"

    def _looks_like_url_or_data_uri(self, value: str) -> bool:
        candidate = value.strip()
        if candidate.lower().startswith("data:image/"):
            return True

        parsed = urlparse(candidate)
        return parsed.scheme in ("http", "https")

    def _normalize_image_mime_type(self, raw_mime_type: Optional[str]) -> str:
        if not raw_mime_type:
            return "image/png"

        # Drop parameters and enforce lowercase type/subtype for data URI compatibility.
        mime_type = raw_mime_type.split(";", 1)[0].strip().lower()
        if not mime_type.startswith("image/"):
            return "image/png"

        if mime_type == "image/jpg":
            return "image/jpeg"

        return mime_type
