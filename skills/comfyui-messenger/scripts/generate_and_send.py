#!/usr/bin/env python3
import argparse
import copy
import json
import os
import random
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

Z_TURBO_SUFFIX = (
    "high detail, clean composition, coherent anatomy, sharp focus, "
    "cinematic lighting, rich color contrast, professional digital art, 4k"
)
Z_TURBO_NEGATIVE = (
    "lowres, blurry, worst quality, low quality, jpeg artifacts, "
    "deformed, extra fingers, bad hands, bad anatomy, text, watermark, logo"
)

CLIP_TEXT_CLASSES = {
    "CLIPTextEncode",
    "CLIPTextEncodeSDXL",
    "CLIPTextEncodeSDXLRefiner",
}


def http_json(method: str, url: str, payload=None, headers=None, timeout=60):
    data = None
    merged_headers = {"Content-Type": "application/json"}
    if headers:
        merged_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = Request(url=url, data=data, method=method, headers=merged_headers)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_bytes(url: str, timeout=120):
    req = Request(url=url, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def apply_override(workflow: dict, key: str, value: str):
    # Expected format: node_id.inputs.field=value
    parts = key.split(".")
    if len(parts) != 3 or parts[1] != "inputs":
        raise ValueError(f"Invalid override key: {key}")
    node_id, _, field = parts
    if node_id not in workflow:
        raise KeyError(f"Node id not found in workflow: {node_id}")
    if "inputs" not in workflow[node_id]:
        raise KeyError(f"Node has no inputs: {node_id}")

    parsed_value = value
    if value.lower() in ("true", "false"):
        parsed_value = value.lower() == "true"
    else:
        try:
            if "." in value:
                parsed_value = float(value)
            else:
                parsed_value = int(value)
        except ValueError:
            parsed_value = value

    workflow[node_id]["inputs"][field] = parsed_value


def submit_prompt(base_url: str, prompt: dict):
    url = f"{base_url.rstrip('/')}/prompt"
    payload = {"prompt": prompt, "client_id": str(uuid.uuid4())}
    data = http_json("POST", url, payload=payload)
    prompt_id = data.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"Failed to submit prompt: {data}")
    return prompt_id


def wait_for_history(base_url: str, prompt_id: str, timeout_sec=600, interval_sec=2):
    url = f"{base_url.rstrip('/')}/history/{prompt_id}"
    deadline = time.time() + timeout_sec
    last_error = None
    while time.time() < deadline:
        try:
            data = http_json("GET", url, payload=None, headers={})
            if prompt_id in data:
                return data[prompt_id]
        except Exception as exc:
            last_error = exc
        time.sleep(interval_sec)
    if last_error:
        raise TimeoutError(f"Timed out waiting for render. Last error: {last_error}")
    raise TimeoutError("Timed out waiting for render.")


def extract_first_image_output(history_item: dict):
    outputs = history_item.get("outputs", {})
    for node_data in outputs.values():
        images = node_data.get("images", [])
        if images:
            return images[0]
    raise RuntimeError("No image output found in ComfyUI history outputs.")


def download_image(base_url: str, image_meta: dict, outdir: Path):
    params = {
        "filename": image_meta["filename"],
        "subfolder": image_meta.get("subfolder", ""),
        "type": image_meta.get("type", "output"),
    }
    view_url = f"{base_url.rstrip('/')}/view?{urlencode(params)}"
    content, content_type = http_bytes(view_url)

    ext = ".png"
    if "jpeg" in content_type or "jpg" in content_type:
        ext = ".jpg"
    elif "webp" in content_type:
        ext = ".webp"

    outdir.mkdir(parents=True, exist_ok=True)
    target = outdir / f"comfy_{int(time.time())}{ext}"
    target.write_bytes(content)
    return target


def parse_args():
    p = argparse.ArgumentParser(
        description="Trigger ComfyUI workflow, download first image, and print the local file path."
    )
    p.add_argument(
        "--workflow",
        default="",
        help="Path to ComfyUI workflow JSON (UI export or API prompt JSON).",
    )
    p.add_argument(
        "--base-url",
        default=os.getenv("COMFYUI_BASE_URL", "http://barryko-mini:8000"),
        help="ComfyUI base URL.",
    )
    p.add_argument("--prompt", default="", help="Prompt text for UI workflow mode.")
    p.add_argument("--negative", default="", help="Negative prompt for UI workflow mode.")
    p.add_argument("--negative-node-id", default="", help="API workflow node id to receive negative prompt.")
    p.add_argument("--positive-node-id", default="", help="API workflow node id to receive positive prompt.")
    p.add_argument(
        "--no-enhance",
        action="store_true",
        help="Disable automatic z-image-turbo prompt enhancement.",
    )
    p.add_argument("--node-id", type=int, default=57, help="Target node id for UI workflow mode.")
    p.add_argument("--prompt-index", type=int, default=0, help="widgets_values index for prompt.")
    p.add_argument("--negative-index", type=int, default=1, help="widgets_values index for negative prompt.")
    p.add_argument("--seed-index", type=int, default=4, help="widgets_values index for seed.")
    p.add_argument("--seed", type=int, default=-1, help="Use explicit seed. -1 means random.")
    p.add_argument("--set", action="append", default=[], help="Override in form node.inputs.field=value")
    p.add_argument(
        "--outdir",
        default=os.getenv(
            "COMFYUI_OUTDIR",
            "~/.openclaw/workspace/tmp/comfyui-messenger",
        ),
        help="Local output directory",
    )
    p.add_argument("--timeout", type=int, default=600, help="Render timeout seconds")
    return p.parse_args()


def resolve_workflow_path(args):
    if args.workflow:
        return Path(args.workflow)
    skill_root = Path(__file__).resolve().parents[1]
    default_path = skill_root / "workflow_api.json"
    if default_path.exists():
        return default_path
    raise FileNotFoundError(
        "Workflow file not found. Pass --workflow or put workflow_api.json next to SKILL.md."
    )


def _ui_find_node(workflow: dict, node_id: int):
    for node in workflow.get("nodes", []):
        if int(node.get("id", -1)) == int(node_id):
            return node
    raise KeyError(f"Node id not found in UI workflow: {node_id}")


def _set_widget_value(node: dict, idx: int, value):
    widgets = node.get("widgets_values")
    if not isinstance(widgets, list):
        raise KeyError("UI workflow node has no widgets_values list.")
    if idx < 0 or idx >= len(widgets):
        raise IndexError(f"widgets_values index out of range: {idx} (len={len(widgets)})")
    widgets[idx] = value


def apply_ui_prompt_overrides(workflow: dict, args):
    node = _ui_find_node(workflow, args.node_id)
    if args.prompt:
        _set_widget_value(node, args.prompt_index, args.prompt)
    if args.negative:
        _set_widget_value(node, args.negative_index, args.negative)
    seed = args.seed if args.seed >= 0 else random.randint(1, 10**12)
    try:
        _set_widget_value(node, args.seed_index, seed)
    except Exception:
        # Some UI workflows may not expose seed as a widget; skip in that case.
        pass


def is_text_encode_class(node: dict) -> bool:
    return node.get("class_type") in CLIP_TEXT_CLASSES


def apply_api_prompt_overrides(workflow: dict, args):
    text_nodes = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if not is_text_encode_class(node):
            continue
        inputs = node.get("inputs", {})
        if isinstance(inputs, dict) and "text" in inputs:
            text_nodes.append((node_id, node))

    positive_node_id = None
    if args.prompt and args.positive_node_id:
        node = workflow.get(args.positive_node_id)
        if isinstance(node, dict) and isinstance(node.get("inputs"), dict) and "text" in node["inputs"]:
            node["inputs"]["text"] = args.prompt
            positive_node_id = args.positive_node_id
        else:
            print(
                f"WARN: positive-node-id not found or invalid: {args.positive_node_id}",
                file=sys.stderr,
            )

    if args.prompt and text_nodes and positive_node_id is None:
        # Prefer a non-empty prompt node for positive prompt.
        positive = None
        for node_id, node in text_nodes:
            text_val = str(node.get("inputs", {}).get("text", "")).strip()
            if text_val:
                positive = (node_id, node)
                break
        if positive is None:
            positive = text_nodes[0]
        positive[1]["inputs"]["text"] = args.prompt
        positive_node_id = positive[0]

    negative_applied = False
    if args.negative and args.negative_node_id:
        node = workflow.get(args.negative_node_id)
        if isinstance(node, dict) and isinstance(node.get("inputs"), dict) and "text" in node["inputs"]:
            node["inputs"]["text"] = args.negative
            negative_applied = True
        else:
            print(
                f"WARN: negative-node-id not found or invalid: {args.negative_node_id}",
                file=sys.stderr,
            )

    if args.negative and text_nodes and not negative_applied:
        if len(text_nodes) == 1:
            # Avoid overwriting the only text node (likely positive prompt).
            print(
                "WARN: Only one text-encode node found; skipping negative prompt.",
                file=sys.stderr,
            )
        else:
            # Prefer an empty prompt node for negative prompt.
            negative = None
            for node_id, node in text_nodes:
                if positive_node_id is not None and node_id == positive_node_id:
                    continue
                text_val = str(node.get("inputs", {}).get("text", "")).strip()
                if not text_val:
                    negative = (node_id, node)
                    break
            if negative is None:
                # Fall back to a different node than positive if possible.
                for node_id, node in text_nodes:
                    if positive_node_id is None or node_id != positive_node_id:
                        negative = (node_id, node)
                        break
            if negative is not None:
                negative[1]["inputs"]["text"] = args.negative

    if args.seed >= 0:
        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            if node.get("class_type") != "KSampler":
                continue
            inputs = node.get("inputs", {})
            if isinstance(inputs, dict) and "seed" in inputs:
                inputs["seed"] = args.seed
                break


def build_enhanced_prompts(args):
    if not args.prompt:
        return args.prompt, args.negative
    if args.no_enhance:
        return args.prompt, args.negative

    base = args.prompt.strip().rstrip(",")
    enhanced = f"{base}, {Z_TURBO_SUFFIX}"

    negative = args.negative.strip()
    if negative:
        negative = f"{negative}, {Z_TURBO_NEGATIVE}"
    else:
        negative = Z_TURBO_NEGATIVE
    return enhanced, negative


def main():
    args = parse_args()
    if not args.base_url:
        raise RuntimeError("Missing --base-url and COMFYUI_BASE_URL")

    workflow_path = resolve_workflow_path(args)
    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    with workflow_path.open("r", encoding="utf-8") as f:
        workflow = json.load(f)

    args.prompt, args.negative = build_enhanced_prompts(args)

    prompt = copy.deepcopy(workflow)
    is_ui_workflow = isinstance(prompt, dict) and isinstance(prompt.get("nodes"), list)
    if is_ui_workflow:
        apply_ui_prompt_overrides(prompt, args)
    else:
        apply_api_prompt_overrides(prompt, args)
        for item in args.set:
            if "=" not in item:
                raise ValueError(f"Invalid --set format: {item}")
            key, value = item.split("=", 1)
            apply_override(prompt, key, value)

    prompt_id = submit_prompt(args.base_url, prompt)
    history_item = wait_for_history(args.base_url, prompt_id, timeout_sec=args.timeout)
    image_meta = extract_first_image_output(history_item)
    outdir = Path(os.path.expanduser(args.outdir))
    image_path = download_image(args.base_url, image_meta, outdir)

    # Print absolute path so the calling agent can send the image via its own channel.
    print(str(image_path.resolve()))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
