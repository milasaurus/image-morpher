# image morpher

I kept finding myself switching between Claude and Luma — paste a prompt into Luma, see the result, go back to Claude to refine the prompt, paste it again. That one extra step added real friction. Luma is great at reasoning about images, but the image is only as good as the prompt, and writing that prompt well required a separate tool and a separate context switch.

Image morpher removes the switch. Pick the better image each round; Claude interprets what you preferred and writes the next prompt. Your taste drives it, not your prompt engineering.

<img width="1087" height="395" alt="image" src="https://github.com/user-attachments/assets/be5c6beb-525d-4ed7-8e9f-cfec3efa86ef" />

<img width="470" height="305" alt="image" src="https://github.com/user-attachments/assets/cad966b9-0fee-4221-9993-24675d78338b" />

---

## Setup

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), a [Luma](https://lumalabs.ai) API key, and an [Anthropic](https://console.anthropic.com) API key.

```bash
git clone <repo-url>
cd image-morpher
```

Add your API keys:

```bash
cp api/.env.example api/.env
# edit api/.env and fill in LUMAAI_API_KEY and ANTHROPIC_API_KEY
```

```bash
make dev
```

Open **http://localhost:8080**. Press Ctrl+C to stop both servers.

---

## How to use

1. **Type a prompt** and click Generate. Two images appear in ~50 seconds.
2. **Click the image you prefer.** It becomes the anchor for the next round.
3. **Pick an intent:**
   - 🎯 *Refine this* — one focused change, stay close
   - 🎨 *New subject, same look* — keep the mood and style, swap what's in it
   - 🌐 *New scene, same subject* — keep what's in it, change the setting
4. **Repeat** until you're satisfied.
5. **Click Done** to open the final image. Use Cmd/Ctrl+S to save it.

---

## Notes

- Each generation takes 30–60 seconds — this is Luma UNI-1's latency.
- Image URLs expire after ~1 hour. Save your result before closing the session.
- Findings from building this are in [`NOTES.md`](NOTES.md).
