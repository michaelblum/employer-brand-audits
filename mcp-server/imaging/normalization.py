from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from PIL import Image


DEFAULT_NORMALIZATION_POLICY: dict[str, Any] = {
    "max_rendered_height": 4000,
    "codec": "source",
    "quality": 85,
    "compression_level": 6,
    "optimize": True,
    "subtypes": {},
}

CODEC_EXTENSIONS = {
    "jpeg": ".jpg",
    "jpg": ".jpg",
    "png": ".png",
    "webp": ".webp",
}


def load_normalization_policy(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        return copy.deepcopy(DEFAULT_NORMALIZATION_POLICY)
    with Path(path).expanduser().open(encoding="utf-8") as handle:
        return merge_policy(json.load(handle))


def merge_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    merged = copy.deepcopy(DEFAULT_NORMALIZATION_POLICY)
    if not policy:
        return merged
    for key, value in policy.items():
        if key == "subtypes" and isinstance(value, dict):
            merged["subtypes"].update(value)
        else:
            merged[key] = value
    return merged


def policy_for_subtype(
    artifact_subtype: str | None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = merge_policy(policy)
    subtypes = resolved.get("subtypes")
    override = subtypes.get(artifact_subtype) if isinstance(subtypes, dict) and artifact_subtype else None
    if isinstance(override, dict):
        merged = {key: value for key, value in resolved.items() if key != "subtypes"}
        merged.update(override)
        return merged
    return {key: value for key, value in resolved.items() if key != "subtypes"}


def _codec_for_path(path: Path, codec: str) -> str:
    if codec == "source":
        suffix = path.suffix.lower().lstrip(".")
        if suffix == "jpg":
            return "jpeg"
        return suffix or "png"
    if codec == "jpg":
        return "jpeg"
    return codec


def _output_path_for(source_path: Path, output_path: str | Path | None, codec: str) -> Path:
    if output_path is not None:
        return Path(output_path).expanduser()
    if codec == "source":
        return source_path
    extension = CODEC_EXTENSIONS.get(codec, source_path.suffix)
    return source_path.with_suffix(extension)


def _image_for_codec(image: Image.Image, codec: str, matte: str = "white") -> Image.Image:
    if codec in {"jpeg", "jpg"} and image.mode in {"RGBA", "LA", "P"}:
        base = Image.new("RGB", image.size, matte)
        rgba = image.convert("RGBA")
        base.paste(rgba, mask=rgba.getchannel("A"))
        return base
    if codec in {"jpeg", "jpg"}:
        return image.convert("RGB")
    return image


def _save_image(image: Image.Image, output_path: Path, codec: str, policy: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    optimize = bool(policy.get("optimize", True))
    if codec in {"jpeg", "jpg"}:
        image.save(
            output_path,
            "JPEG",
            quality=int(policy.get("quality", 85)),
            optimize=optimize,
        )
        return
    if codec == "webp":
        image.save(
            output_path,
            "WEBP",
            quality=int(policy.get("quality", 85)),
            method=int(policy.get("compression_level", 6)),
        )
        return
    if codec == "png":
        image.save(
            output_path,
            "PNG",
            optimize=optimize,
            compress_level=int(policy.get("compression_level", 6)),
        )
        return
    image.save(output_path)


def normalize_image_artifact(
    source_path: str | Path,
    artifact_subtype: str | None = None,
    policy: dict[str, Any] | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_path).expanduser()
    resolved_policy = policy_for_subtype(artifact_subtype, policy)
    requested_codec = str(resolved_policy.get("codec", "source")).lower()
    codec = _codec_for_path(source, requested_codec)
    output = _output_path_for(source, output_path, requested_codec if requested_codec == "source" else codec)
    max_height = int(resolved_policy.get("max_rendered_height", 4000))

    with Image.open(source) as raw:
        image = raw.copy()
    source_dimensions = {"width": image.width, "height": image.height}

    resized = False
    if max_height > 0 and image.height > max_height:
        ratio = max_height / image.height
        image = image.resize(
            (max(1, round(image.width * ratio)), max_height),
            Image.LANCZOS,
        )
        resized = True

    image = _image_for_codec(image, codec, str(resolved_policy.get("matte", "white")))
    _save_image(image, output, codec, resolved_policy)

    return {
        "source_path": str(source),
        "output_path": str(output),
        "artifact_subtype": artifact_subtype,
        "source_dimensions": source_dimensions,
        "output_dimensions": {"width": image.width, "height": image.height},
        "resized": resized,
        "codec": codec,
        "policy": resolved_policy,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize a composed image artifact.")
    parser.add_argument("source_path", type=Path)
    parser.add_argument("--artifact-subtype")
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output-path", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = normalize_image_artifact(
        args.source_path,
        artifact_subtype=args.artifact_subtype,
        policy=load_normalization_policy(args.policy),
        output_path=args.output_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
