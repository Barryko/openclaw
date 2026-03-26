---
name: comfyui-messenger
description: Generate images through ComfyUI at barryko-mini:8000 from user prompt text and download the result locally. Use when user asks Openclaw to draw, generate, render, create an image, or says things like "請幫我產生一張圖" and expects the image returned in chat.
---

# ComfyUI Messenger

Use this skill to run a ComfyUI workflow, wait for render completion, and download the image locally.
It automatically enhances user prompt text for Z Image Turbo unless `--no-enhance` is provided.

## Required Inputs (Minimal)

- `COMFYUI_BASE_URL` (default already set in script: `http://barryko-mini:8000`)
- `workflow_api.json` (can be ComfyUI API JSON or your tested UI workflow JSON)
- A prompt string

## Optional Environment Variables

- `COMFYUI_BASE_URL`

## Basic Command (Prompt Only)

```bash
python3 skills/comfyui-messenger/scripts/generate_and_send.py \
  --prompt "A cinematic portrait, ultra detailed"
```

Default download folder: `~/Users/ai-sandbox~/.openclaw/workspace/tmp/comfyui-messenger`

## Prompt Auto-Enhancement

- Default behavior: append Z Image Turbo friendly quality/style tokens.
- Default behavior: inject a safe negative prompt to reduce blur/artifacts/bad anatomy.
- Disable enhancement when needed:

```bash
python3 skills/comfyui-messenger/scripts/generate_and_send.py \
  --prompt "minimal flat icon of a cat" \
  --no-enhance
```

## Agent Execution Rule

⚠️ **MANDATORY: You MUST complete ALL steps below. Do NOT stop after running the script.**
⚠️ **Run exactly ONE command execution per user request. Do NOT retry or re-run unless the user explicitly asks.**
⚠️ **IMAGE GENERATION IS SLOW — wait at least 10 minutes before considering a timeout. Do NOT abort, retry, or give up before 10 minutes have elapsed.**

When user requests image generation:

### Step 1 — Build Prompt
Build a clear English prompt from user intent.

### Step 2 — Run Script
```bash
python3 ~/.openclaw/workspace/skills/comfyui-messenger/scripts/generate_and_send.py \
  --prompt "<final prompt>"
```

The script prints the absolute local file path to stdout on success, or writes `ERROR: ...` to stderr on failure.

> ⚠️ **Rendering can take several minutes.** Wait at least 10 minutes for the script to complete. Do NOT cancel or re-run due to perceived slowness.

### Step 3 — Capture Result
Read the absolute path printed to stdout — that is the generated image file.
If the script exits with an error (stderr), report the error to the user and stop.

### Step 4 — SEND TO CHAT (MANDATORY — DO NOT SKIP)

**This step is required. You MUST ensure the image is sent.**
**If you do NOT send the image, treat the job as FAILED and do NOT claim success.**

Use the absolute path from Step 3 and send via the calling agent's own channel mechanism:

```
message.send(
  channel="<current channel>",
  target="<chat_id or channel target>",
  message="圖片生成完成 ✅",
  filePath="<absolute path from Step 3>"
)
```

> ⚠️ `message` must NEVER be empty. Use `"圖片生成完成 ✅"` or `"."` as default.

### Step 5 — Confirm
After sending, confirm to the user that the image was sent successfully.

---

## If Using Your Current Z-Image-Turbo UI Workflow

```bash
python3 skills/comfyui-messenger/scripts/generate_and_send.py \
  --workflow /absolute/path/to/workflow_api.json \
  --prompt "A cinematic portrait, ultra detailed" \
  --node-id 57 \
  --prompt-index 0 \
  --seed-index 4
```

## SDXL Support

API workflows with `CLIPTextEncodeSDXL` / `CLIPTextEncodeSDXLRefiner` are supported automatically.

Example forcing positive/negative nodes:

```bash
python3 /Users/ai-sandbox/.openclaw/workspace/skills/comfyui-messenger/scripts/generate_and_send.py \
  --prompt "A cinematic portrait, ultra detailed" \
  --negative "blurry, low detail, bad anatomy" \
  --positive-node-id 57:27 \
  --negative-node-id 57:34
```

Note: If the API workflow only has one `CLIPTextEncode`-style node, negative prompts are skipped to avoid overwriting the positive prompt. You can force target nodes with `--positive-node-id` and `--negative-node-id`.

## Notes

- For UI workflow JSON, this script edits `widgets_values` on the target node.
- For API prompt JSON, use `--set node.inputs.field=value` overrides.
- The script only downloads the image locally — YOU must send it via `message.send`.

## Delivery Rule (Summary)

The script only generates and downloads the image. Delivery is always handled by the calling agent via `message.send` with `filePath` + non-empty `message`, regardless of channel.
