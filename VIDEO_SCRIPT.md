# Aqua Elya — Video Script (3 minutes)

## Target: Kaggle Gemma 4 Good Hackathon submission video

---

### SHOT 1: The Problem (0:00–0:30)
**[Camera on NFT system in garden — 108 cells, PVC channels, two buckets]**

> "This is my hydroponic system. 108 plants, nutrient film technique,
> two aerated reservoirs. It feeds my family.
>
> But if this pump stops at 3 AM — in Louisiana July heat — the roots
> dry out in 20 minutes and I lose everything.
>
> Commercial SCADA monitoring? Fifty thousand dollars. I know because
> I'm a SCADA tech — I've installed those systems.
>
> What if the same monitoring cost eighty-five bucks?"

---

### SHOT 2: The Solution (0:30–1:15)
**[Screen recording: terminal running `python3 scada_loop.py --fast`]**

> "This is Aqua Elya. Gemma 4 running locally on my laptop, making
> real-time SCADA decisions about my crops.
>
> [Point to sensor readings on screen]
> Every 30 seconds it reads flow rate, pH, EC, water temperature,
> reservoir levels. Then it asks Gemma 4: what should we do?
>
> [Point to Gemma's function call output]
> See that? Gemma didn't just say 'OK.' It noticed flow was 10% below
> target and logged it as a trend to watch. A PLC wouldn't catch that.
>
> It uses native function calling — set_pump, alert_farmer, adjust_flow.
> The AI IS the PLC. Except this one explains its reasoning in English.
> Or French. Or Bambara. Or Arabic."

---

### SHOT 3: Dual Brain (1:15–1:50)
**[Split screen: E4B terminal (fast) and 26B analyst terminal (deep)]**

> "But here's what makes this different from every other entry.
>
> Two Gemma 4 models. Same laptop. Different jobs.
>
> [Point to left terminal]
> The E4B runs on GPU — 25-second decisions. Reflexive. 'Is the pump OK
> right now?' That's the operator watching the screens.
>
> [Point to right terminal]
> The 26B runs on CPU — takes two minutes, but look at what it says.
>
> [Read analyst output]
> 'pH trending up 0.04 per minute. EC declining in correlation.
> Prediction: pH will exceed threshold in 60 minutes.
> Recommendation: check dosing pump — may be stuck on.'
>
> That's a shift supervisor reading trend charts. On a laptop."

---

### SHOT 4: The Hardware (1:50–2:20)
**[Camera panning over sensor components — assembled or in their packaging on a workbench]**

> "Flow meter — six bucks. pH probe — twelve. Temperature sensor — three.
> ESP32 for WiFi — five. Total sensor kit: eighty-five dollars.
>
> [Hold up laptop]
> This is a used laptop. Runs both Gemma models. No internet. No cloud.
> No subscription. No API costs.
>
> A farmer in Mali can run this. A refugee camp in Jordan can run this.
> A school classroom in Mississippi can run this.
>
> [Cut to NFT system, growing crops]
> The brain is finished. The crops are real. The plumbing — that's the
> next phase, and it's the part I've spent twenty years doing for a
> living."

---

### SHOT 5: Why It Matters (2:20–2:50)
**[Camera on Scott, NFT system in background]**

> "I'm a SCADA tech. I've built the fifty-thousand-dollar systems.
> They work great — if you can afford them.
>
> 800 million people face food insecurity. Hydroponics can grow food
> anywhere with 90% less water. But without monitoring, it's fragile.
>
> Gemma 4 changes that equation. Function calling replaces ladder logic.
> Multimodal replaces separate camera systems. And it runs offline —
> because the people who need this most don't have reliable internet.
>
> The architecture is finished. The hydroponics are running. The wiring
> happens next — and then we'll know exactly how much of a SCADA tech's
> career a $5 ESP32 can replace."

---

### SHOT 6: Call to Action (2:50–3:00)
**[Screen showing GitHub repo]**

> "Clone the repo. Run it in two minutes with simulated sensors.
> Or wire it up for real — the ESP32 firmware is included.
>
> Aqua Elya. Gemma 4. Eighty-five dollars between a family and a
> lost harvest."

**[End card: GitHub URL, Elyan Labs logo]**

---

## Production Notes

- Film at golden hour for warm Louisiana light on NFT system
- Terminal recordings: use `--fast` mode so readings come every 5 seconds
- For the analyst demo, pre-generate ~20 readings then run analyst.py live
- Keep the ESP32 and sensors visible but don't over-explain wiring
- Webcam pointed at actual crops during the SCADA loop demo
- Total runtime target: 2:45–2:55 (leave buffer under 3:00)
