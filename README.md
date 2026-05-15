# image morpher

Getting from "pretty good" to "exactly right" in generative image tools means manually translating taste into prompt edits. Most people don't speak that language fluently.

Image Morpher replaces prompt tweaking with picking. Choose the better image each round; Claude interprets what you preferred and writes the next prompt. Your taste drives it, not your prompt engineering.

<img width="1087" height="395" alt="image" src="https://github.com/user-attachments/assets/be5c6beb-525d-4ed7-8e9f-cfec3efa86ef" />

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
