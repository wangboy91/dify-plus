from typing import Generator

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class TextToImageTool(Tool):
    def _invoke(self, tool_parameters: dict) -> Generator[ToolInvokeMessage, None, None]:
        credentials = self.runtime.credentials or {}
        api_key = credentials.get("ark_api_key")
        base_url = credentials.get("base_url") or "https://ark.cn-beijing.volces.com"
        model = tool_parameters.get("model") or "ep-20260125201054-pfrb4"

        prompt = tool_parameters.get("prompt")
        if not prompt:
            yield self.create_text_message("prompt is required")
            return

        size = tool_parameters.get("size") or "4K"
        sequential_mode = tool_parameters.get("sequential_image_generation") or "disabled"
        max_images = tool_parameters.get("max_images")
        response_format = tool_parameters.get("response_format") or "url"
        watermark = tool_parameters.get("watermark")
        if watermark is None:
            watermark = True

        payload = {
            "model": model,
            "prompt": prompt,
            "sequential_image_generation": sequential_mode,
            "response_format": response_format,
            "size": size,
            "watermark": watermark,
        }
        if sequential_mode == "auto" and max_images:
            payload["sequential_image_generation_options"] = {
                "max_images": int(max_images)
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
