# image morpher

Generative image tools reset on every generation — you lose what made the last image good. Image morpher lets you keep it. Pick the better image each round and it becomes your anchor; a new candidate is generated in the direction you chose. Repeat until you're happy.

Between rounds, Claude looks at both images and writes a prompt that embodies your intent — refining the details, borrowing the look for a new subject, or transplanting the subject to a new scene. You're doing gradient descent on an image, with yourself as the loss function.

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
