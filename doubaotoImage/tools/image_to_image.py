import base64
import json
import os
from typing import Generator, Optional
from urllib.parse import urlparse

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class ImageToImageTool(Tool):
    def _invoke(self, tool_parameters: dict) -> Generator[ToolInvokeMessage, None, None]:
        credentials = self.runtime.credentials or {}
        api_key = credentials.get("ark_api_key")
        base_url = credentials.get("base_url") or "https://ark.cn-beijing.volces.com"
        model = credentials.get("model") or "ep-20260125201054-pfrb4"

        prompt = tool_parameters.get("prompt")
        if not prompt:
            yield self.create_text_message("prompt is required")
            return

        image_input = yield from self._resolve_image_from_parameters(tool_parameters)
        if not image_input:
            yield self.create_text_message(
                "image is required or local file content could not be resolved"
            )
            return

        size = tool_parameters.get("size") or "4K"
        response_format = tool_parameters.get("response_format") or "url"
        watermark = tool_parameters.get("watermark")
        if watermark is None:
            watermark = True

        payload = {
            "model": model,
            "prompt": prompt,
            "image": image_input,
            "response_format": response_format,
            "size": size,
            "watermark": watermark,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url.rstrip('/')}/api/v3/images/generations"
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()

        images = data.get("data") or []
        for image in images:
            image_url = image.get("url")
            if image_url:
                yield self.create_image_message(image_url)

        yield self.create_json_message(
            {
                "model": data.get("model"),
                "created": data.get("created"),
                "data": images,
                "usage": data.get("usage"),
            }
        )

    def _resolve_image_from_parameters(self, tool_parameters: dict) -> Generator[ToolInvokeMessage, None, Optional[str]]:
        yield self.create_text_message("[DEBUG] Starting image resolution...")
        for key in ["image", "reference_image", "sys.files", "sys_files"]:
            yield self.create_text_message(f"[DEBUG] Checking parameter: '{key}'")
            resolved = yield from self._resolve_image_input(tool_parameters.get(key))
            if resolved:
                yield self.create_text_message(f"[DEBUG] Found and resolved image from '{key}'")
                return resolved

        skip_keys = {"prompt", "size", "response_format", "watermark", "model"}
        for key, value in tool_parameters.items():
            if key in skip_keys:
                continue
            resolved = yield from self._resolve_image_input(value)
            if resolved:
                yield self.create_text_message(f"[DEBUG] Found and resolved image from fallback parameter '{key}'")
                return resolved

        yield self.create_text_message("[DEBUG] Image resolution finished, no image found.")
        return None

    def _resolve_image_input(self, image_parameter) -> Generator[ToolInvokeMessage, None, Optional[str]]:
        if not image_parameter:
            return None

        if isinstance(image_parameter, list):
            yield self.create_text_message("[DEBUG] Processing list of potential images...")
            for item in image_parameter:
                if resolved_item := (yield from self._resolve_image_input(item)):
                    return resolved_item
            return None

        if isinstance(image_parameter, str) and image_parameter.strip().startswith("{"):
            try:
                yield self.create_text_message("[DEBUG] Parsing JSON string to resolve image...")
                parsed = json.loads(image_parameter)
                return (yield from self._resolve_image_input(parsed))
            except Exception:
                yield self.create_text_message("[DEBUG] Failed to parse string as JSON.")
                pass

        if isinstance(image_parameter, str) and image_parameter.strip():
            normalized = image_parameter.strip()
            if self._looks_like_url_or_data_uri(normalized):
                yield self.create_text_message("[DEBUG] Using provided string as URL or Data URI.")
                return normalized
            yield self.create_text_message("[DEBUG] Treating string as a potential file ID.")
            return (yield from self._file_id_to_data_uri(normalized))

        if isinstance(image_parameter, dict):
            yield self.create_text_message("[DEBUG] Extracting image from dictionary object...")
            return (yield from self._extract_image_input(image_parameter))

        yield self.create_text_message("[DEBUG] Treating value as a potential file object...")
        object_candidate = yield from self._extract_from_file_object(image_parameter)
        if object_candidate:
            return object_candidate

        return None

    def _extract_image_input(self, image_input: dict) -> Generator[ToolInvokeMessage, None, Optional[str]]:
        transfer_method = image_input.get("transfer_method")

        if transfer_method == "remote_url":
            yield self.create_text_message("[DEBUG] transfer_method is 'remote_url'.")
            url_value = image_input.get("url")
            if isinstance(url_value, str) and self._looks_like_url_or_data_uri(url_value):
                return url_value.strip()
            return None

        if transfer_method == "local_file":
            yield self.create_text_message("[DEBUG] transfer_method is 'local_file'.")
            file_id = self._extract_file_id(image_input) or self._extract_file_id(image_input.get("value", {}))
            data_uri = (yield from self._file_id_to_data_uri(file_id)) if file_id else None
            if data_uri:
                return data_uri
            yield self.create_text_message("[DEBUG] 'local_file' did not yield content, falling back to URL.")
            return self._url_to_data_uri(image_input.get("url") or image_input.get("remote_url"))

        # Support upstream variable mapping where transfer_method might be absent.
        for key in ["url", "remote_url"]:
            url_value = image_input.get(key)
            if isinstance(url_value, str) and self._looks_like_url_or_data_uri(url_value):
                return url_value.strip()

        nested_value = image_input.get("value")
        if isinstance(nested_value, dict):
            nested_image = yield from self._extract_image_input(nested_value)
            if nested_image:
                return nested_image

        file_id = self._extract_file_id(image_input) or self._extract_file_id(image_input.get("value", {}))
        if file_id:
            yield self.create_text_message(f"[DEBUG] Found file ID '{file_id}' in dict, attempting to read.")
            data_uri = yield from self._file_id_to_data_uri(file_id)
            if data_uri:
                return data_uri

        yield self.create_text_message("[DEBUG] No file ID found, falling back to URL attribute.")
        return self._url_to_data_uri(image_input.get("url") or image_input.get("remote_url"))

    def _extract_from_file_object(self, value) -> Generator[ToolInvokeMessage, None, Optional[str]]:
        if value is None:
            return None

        # Prefer internal file-id lookup to avoid FILES_URL dependency.
        for key in ["id", "related_id", "file_id", "upload_file_id"]:
            file_id = self._safe_getattr(value, key)
            if isinstance(file_id, str) and file_id.strip():
                yield self.create_text_message(f"[DEBUG] Found file ID '{file_id}' in object attribute '{key}'.")
                data_uri = yield from self._file_id_to_data_uri(file_id.strip())
                if data_uri:
                    return data_uri

        # SDK file model may expose a lazy-loaded bytes property `blob`.
        blob = self._safe_getattr(value, "blob")
        if isinstance(blob, bytes) and blob:
            mime_type = self._normalize_image_mime_type(self._safe_getattr(value, "mime_type"))
            return f"data:{mime_type};base64,{base64.b64encode(blob).decode('utf-8')}"

        yield self.create_text_message("[DEBUG] No file ID or blob found on object, falling back to URL attribute.")
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
            return getattr(obj, attr, None)
        except Exception:
            return None

    def _extract_file_id(self, data: dict) -> Optional[str]:
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

        yield self.create_text_message(f"[DEBUG] Reading content for file ID: {file_id}")
        file_content, mime_type = yield from self._read_file_content(file_id)
        if not file_content:
            yield self.create_text_message(f"[DEBUG] Failed to read content for file ID: {file_id}")
            return None

        yield self.create_text_message(f"[DEBUG] Successfully read {len(file_content)} bytes for file ID: {file_id}")
        mime_type = self._normalize_image_mime_type(mime_type)
        encoded = base64.b64encode(file_content).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _read_file_content(self, file_id: str) -> Generator[ToolInvokeMessage, None, tuple[Optional[bytes], Optional[str]]]:
        # Preferred path in current SDK runtimes.
        runtime = getattr(self, "runtime", None)
        file_manager = getattr(runtime, "file_manager", None) if runtime else None
        if file_manager:
            getter = getattr(file_manager, "get", None)
            if callable(getter):
                yield self.create_text_message("[DEBUG] Using runtime.file_manager.get() to read file.")
                upload_file = getter(file_id)
                content, mime_type = self._extract_bytes_and_mime(upload_file)
                if content:
                    return content, mime_type
                yield self.create_text_message("[DEBUG] runtime.file_manager.get() returned no content.")

        # Fallback for SDK variants exposing get_file_content on tool/runtime.
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

        yield self.create_text_message("[DEBUG] All methods to read file content failed.")
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

        mime_type = raw_mime_type.split(";", 1)[0].strip().lower()
        if not mime_type.startswith("image/"):
            return "image/png"
        if mime_type == "image/jpg":
            return "image/jpeg"
        return mime_type
