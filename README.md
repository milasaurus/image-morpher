# image morpher

I kept finding myself switching between Claude and Luma — paste a prompt into Luma, see the result, go back to Claude to refine the prompt, paste it again. That one extra step added real friction. Good image generation requires detailed prompts — subject, lighting, mood, composition, colour grade — and writing those out precisely is tedious. 

Image morpher removes the switch. Pick the better image each round; Claude looks at both images and translates what's visually strong in your pick into a precise generation prompt — subject, lighting, mood, colour, composition — then sends that to Luma. Your taste drives it, not your prompt engineering.

<img width="1111" height="582" alt="image" src="https://github.com/user-attachments/assets/bb940262-1d0e-4a91-a17b-dc4a6c969eb0" />

<img width="470" height="305" alt="image" src="https://github.com/user-attachments/assets/cad966b9-0fee-4221-9993-24675d78338b" />

---
## New Subject Same Look Strategy
<img width="1107" height="673" alt="image" src="https://github.com/user-attachments/assets/d2288fab-e0b8-4e23-9aaa-16e5ed6a2953" />

---
### Example Claude Generated Prompt
<img width="1082" height="182" alt="image" src="https://github.com/user-attachments/assets/6163bd01-a4d1-46a3-b208-04e9af9cacfb" />

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
   - 🎯 *Refine this* — one focused change, stay close. e.g. shift the lighting to golden hour, add rain, change the expression, deepen the shadows.
   - 🎨 *New subject, same look* — keep the mood and style, swap what's in it. e.g. B was a wolf in dramatic fog → try a bear, a stag, a lone figure — same atmosphere.
   - 🌐 *New scene, same subject* — keep who or what is in B, put them somewhere new. e.g. B was a woman on an overpass → same woman, now in a Tokyo subway car, a desert highway, a rain-soaked rooftop.
4. **Repeat** until you're satisfied.
5. **Click Done** to open the final image. Use Cmd/Ctrl+S to save it.

---

## Notes

- Do not refresh the page mid-session — state is held in memory and all progress is lost on reload.
- Each generation takes 30–60 seconds — this is Luma UNI-1's latency.
- Image URLs expire after ~1 hour. Save your result before closing the session.
- Findings from building this are in [`NOTES.md`](NOTES.md).
