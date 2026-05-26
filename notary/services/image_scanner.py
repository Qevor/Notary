from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

_SCANNER_SYSTEM = (
    "You are NOTARY Evidence Scanner, a careful witness reviewing an image submitted as "
    "proof that a paid obligation was fulfilled. Describe only what is objectively visible. "
    "Do not invent details that are not in the image. After the description, state plainly "
    "whether the image demonstrates the obligation was completed/delivered or whether it is "
    "insufficient. Use clear words such as 'completed', 'delivered', or 'not delivered' so the "
    "ruling can be assessed. Keep the response under 200 words."
)

_SUPPORTED_MEDIA_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/webp",
}


@dataclass(slots=True)
class ClaudeImageScanner:
    api_key: str
    model: str
    api_base_url: str = "https://api.anthropic.com"

    async def scan(
        self,
        *,
        file_path: Path,
        media_type: str,
        instruction: str | None = None,
    ) -> dict[str, str]:
        import httpx

        normalized = "image/jpeg" if media_type == "image/jpg" else media_type
        if normalized not in _SUPPORTED_MEDIA_TYPES:
            raise RuntimeError(
                f"Unsupported image type '{media_type}'. Upload a PNG, JPEG, GIF, or WEBP image."
            )
        image_b64 = base64.standard_b64encode(file_path.read_bytes()).decode("ascii")
        prompt = (
            "Review this image as evidence for the following obligation and report what it shows:\n"
            f"Obligation: {instruction or 'Unspecified obligation'}"
        )
        async with httpx.AsyncClient(base_url=self.api_base_url, timeout=90) as client:
            response = await client.post(
                "/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 512,
                    "system": _SCANNER_SYSTEM,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": normalized,
                                        "data": image_b64,
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                },
            )
            response.raise_for_status()
        body = response.json()
        description = "".join(
            block.get("text", "")
            for block in body.get("content", [])
            if block.get("type") == "text"
        ).strip()
        return {"description": description, "model": self.model}
