import base64
import json
import os
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
        model = tool_parameters.get("model") or "doubao-seedance-1-5-pro-251215"

        prompt = tool_parameters.get("prompt")
        if not prompt:
            yield self.create_text_message("prompt is required")
            return

        image_urls = yield from self._resolve_all_images(tool_parameters)
        if not image_urls:
            yield self.create_text_message(
                "At least one image is required, or local file content could not be resolved"
            )
            return

        generate_audio = tool_parameters.get("generate_audio", True)
        ratio = tool_parameters.get("ratio", "adaptive")
        duration = tool_parameters.get("duration", 5)
        watermark = tool_parameters.get("watermark", False)
        poll_interval = tool_parameters.get("poll_interval", 5)
        max_polls = tool_parameters.get("max_polls", 120)
        image_role = tool_parameters.get("image_role")

        payload = {
            "model": model,
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                }
            ],
            "generate_audio": generate_audio,
            "ratio": ratio,
            "duration": duration,
            "watermark": watermark,
        }

        for url in image_urls:
            payload["content"].append({"type": "image_url", "image_url": {"url": url}})

        # 根据 API 文档，role 是条件必填的。为 'first_frame' 时可不传。
        # 我们提供一个默认值，但允许用户通过传入空字符串来省略该字段。
        if image_role is None:
            image_role = "first_frame"

        if image_role:
            for item in payload["content"]:
                if item["type"] == "image_url":
                    item["role"] = image_role

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url.rstrip('/')}/api/v3/contents/generations/tasks"

        try:
            yield self.create_text_message("正在创建视频生成任务...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            yield self.create_text_message("任务创建成功，返回内容：")
            yield self.create_json_message(data)

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
                                    yield self.create_file(
                                        data=video_resp.content,
                                        filename="generated_video.mp4",
                                        mime_type="video/mp4",
                                    )
                            except Exception as error:
                                yield self.create_text_message(
                                    f"Note: Could not download video directly: {str(error)}"
                                )

                            yield self.create_text_message("任务成功，返回 JSON 结果：")

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

    def _resolve_all_images(self, tool_parameters: dict) -> Generator[ToolInvokeMessage, None, list[str]]:
        all_images = []
        for key in ["reference_image_url", "reference_image", "image", "sys.files", "sys_files"]:
            resolved_list = yield from self._resolve_image_like_parameter(tool_parameters.get(key))
            all_images.extend(resolved_list)

        # Backward-compatible fallback for previous array-based parameter.
        legacy_images = tool_parameters.get("reference_images")
        if isinstance(legacy_images, list) and legacy_images:
            for item in legacy_images:
                all_images.extend((yield from self._resolve_image_like_parameter(item)))

        skip_keys = {
            "prompt",
            "generate_audio",
            "ratio",
            "duration",
            "watermark",
            "poll_interval",
            "max_polls",
            "model",
        }
        for key, value in tool_parameters.items():
            if key in skip_keys:
                continue
            all_images.extend((yield from self._resolve_image_like_parameter(value)))

        # Deduplicate while preserving order
        return list(dict.fromkeys(all_images))

    def _resolve_image_like_parameter(self, value) -> Generator[ToolInvokeMessage, None, list[str]]:
        if not value:
            return []

        if isinstance(value, list):
            resolved_list = []
            for item in value:
                resolved_list.extend((yield from self._resolve_image_like_parameter(item)))
            return resolved_list

        if isinstance(value, str) and value.strip().startswith("{"):
            try:
                parsed = json.loads(value)
                return (yield from self._resolve_image_like_parameter(parsed))
            except Exception:
                return []

        if isinstance(value, str) and value.strip():
            normalized = value.strip()
            if self._looks_like_url_or_data_uri(normalized):
                return [normalized]
            if data_uri := (yield from self._file_id_to_data_uri(normalized)):
                return [data_uri]
            return []

        if isinstance(value, dict):
            if url := (yield from self._extract_image_url(value)):
                return [url]
            return []

        if object_url := (yield from self._extract_from_file_object(value)):
            return [object_url]

        return []

    def _extract_image_url(self, image_input: dict) -> Generator[ToolInvokeMessage, None, Optional[str]]:
        transfer_method = image_input.get("transfer_method")

        if transfer_method == "remote_url":
            url_value = image_input.get("url")
            if isinstance(url_value, str) and self._looks_like_url_or_data_uri(url_value):
                return url_value.strip()
            return None

        if transfer_method == "local_file":
            file_id = self._extract_file_id(image_input) or self._extract_file_id(image_input.get("value", {}))
            data_uri = (yield from self._file_id_to_data_uri(file_id)) if file_id else None
            if data_uri:
                return data_uri
            return self._url_to_data_uri(image_input.get("url") or image_input.get("remote_url"))

        # Support upstream variable mapping where transfer_method is missing.
        for key in ["url", "remote_url"]:
            url_value = image_input.get(key)
            if isinstance(url_value, str) and self._looks_like_url_or_data_uri(url_value):
                return url_value.strip()

        nested_value = image_input.get("value")
        if isinstance(nested_value, dict):
            nested_url = yield from self._extract_image_url(nested_value)
            if nested_url:
                return nested_url

        file_id = self._extract_file_id(image_input) or self._extract_file_id(image_input.get("value", {}))
        if file_id:
            data_uri = yield from self._file_id_to_data_uri(file_id)
            if data_uri:
                return data_uri

        return self._url_to_data_uri(image_input.get("url") or image_input.get("remote_url"))

    def _extract_from_file_object(self, value) -> Generator[ToolInvokeMessage, None, Optional[str]]:
        if value is None:
            return None

        for key in ["id", "related_id", "file_id", "upload_file_id"]:
            file_id = self._safe_getattr(value, key)
            if isinstance(file_id, str) and file_id.strip():
                data_uri = yield from self._file_id_to_data_uri(file_id.strip())
                if data_uri:
                    return data_uri

        blob = self._safe_getattr(value, "blob")
        if isinstance(blob, bytes) and blob:
            mime_type = self._normalize_image_mime_type(self._safe_getattr(value, "mime_type"))
            return f"data:{mime_type};base64,{base64.b64encode(blob).decode('utf-8')}"

        return self._url_to_data_uri(self._safe_getattr(value, "url"))

    def _url_to_data_uri(self, raw_url) -> Optional[str]:
        if not isinstance(raw_url, str) or not raw_url.strip():
            return None

        url = raw_url.strip()
        if url.lower().startswith("data:image/"):
            return url
        if not (url.startswith("/") or self._looks_like_url_or_data_uri(url)):
            return None

        candidates = [url]
        if url.startswith("/"):
            candidates = []
            for env_key in ["DIFY_INNER_API_URL", "DIFY_API_URL", "DIFY_BASE_URL", "CONSOLE_API_URL"]:
                base = os.getenv(env_key)
                if isinstance(base, str) and base.strip():
                    candidates.append(f"{base.rstrip('/')}{url}")

        for candidate in candidates:
            try:
                response = requests.get(candidate, timeout=20)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type")
                mime_type = self._normalize_image_mime_type(content_type)
                return f"data:{mime_type};base64,{base64.b64encode(response.content).decode('utf-8')}"
            except Exception:
                continue

        return None

    def _safe_getattr(self, obj, attr: str):
        try:
            # Handle both object attributes and dictionary keys
            if hasattr(obj, attr):
                return getattr(obj, attr, None)
            if isinstance(obj, dict):
                return obj.get(attr)
        except Exception:
            return None

    def _extract_file_id(self, data: dict) -> Optional[str]:
        # Dify file variables may expose different id fields depending on node/runtime.
        for key in ["id", "related_id", "file_id", "upload_file_id"]:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        # Handle nested value object for file variables
        nested_value = data.get("value")
        if isinstance(nested_value, dict):
            return self._extract_file_id(nested_value)
        return None

    def _file_id_to_data_uri(self, file_id: Optional[str]) -> Generator[ToolInvokeMessage, None, Optional[str]]:
        if not file_id:
            return None

        file_content, mime_type = yield from self._read_file_content(file_id)
        if not file_content:
            return None

        mime_type = self._normalize_image_mime_type(mime_type)
        return f"data:{mime_type};base64,{base64.b64encode(file_content).decode('utf-8')}"

    def _read_file_content(self, file_id: str) -> Generator[ToolInvokeMessage, None, tuple[Optional[bytes], Optional[str]]]:
        runtime = getattr(self, "runtime", None)
        file_manager = getattr(runtime, "file_manager", None) if runtime else None
        if file_manager:
            getter = getattr(file_manager, "get", None)
            if callable(getter):
                upload_file = getter(file_id)
                content, mime_type = self._extract_bytes_and_mime(upload_file)
                if content:
                    return content, mime_type

        for owner in (self, runtime):
            method = getattr(owner, "get_file_content", None) if owner else None
            if callable(method):
                try:
                    raw = method(file_id)
                    if isinstance(raw, bytes):
                        return raw, None
                    if isinstance(raw, tuple) and raw:
                        first = raw[0]
                        second = raw[1] if len(raw) > 1 else None
                        if isinstance(first, bytes):
                            return first, second if isinstance(second, str) else None
                    if isinstance(raw, dict):
                        content = raw.get("content") or raw.get("bytes") or raw.get("file")
                        mime_type = raw.get("mime_type") or raw.get("mimetype")
                        if isinstance(content, bytes):
                            return content, mime_type if isinstance(mime_type, str) else None
                except Exception:
                    continue

        return None, None

    def _extract_bytes_and_mime(self, upload_file) -> tuple[Optional[bytes], Optional[str]]:
        if not upload_file:
            return None, None

        mime_type = getattr(upload_file, "mime_type", None)

        reader = getattr(upload_file, "read", None)
        if callable(reader):
            try:
                data = reader()
                if isinstance(data, bytes):
                    return data, mime_type
            except Exception:
                pass

        for attr in ["content", "data", "blob"]:
            data = getattr(upload_file, attr, None)
            if isinstance(data, bytes):
                return data, mime_type

        if isinstance(upload_file, dict):
            data = upload_file.get("content") or upload_file.get("data") or upload_file.get("bytes")
            if isinstance(data, bytes):
                mime = upload_file.get("mime_type") or upload_file.get("mimetype")
                return data, mime if isinstance(mime, str) else mime_type

        return None, mime_type

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
