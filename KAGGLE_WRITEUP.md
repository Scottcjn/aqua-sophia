# Aqua Elya: Dual-Brain Hydroponic SCADA Powered by Gemma 4

## When the Pump Stops at 3 AM, Who's Watching the Crops?

I'm a SCADA technician from Louisiana. I've built $50,000 industrial control systems — PLCs, RTUs, 4-20mA loops, the works. I also grow food in a 108-cell NFT hydroponic system in my backyard.

Here's the problem: NFT hydroponics grows food with 90% less water than soil farming. It works on rooftops in Lagos, in refugee camps in Jordan, in school classrooms in rural Mississippi. But it's fragile. If the circulation pump fails for 20 minutes in Louisiana summer heat, the roots dry out and 108 plants die.

Commercial SCADA monitoring costs $50,000+. A small farmer will never afford that. So their system runs blind, and when something goes wrong overnight, they lose the crop.

**Aqua Elya replaces the $50,000 SCADA system with Gemma 4 and $85 in sensors.**

## How It Works

Every 30 seconds, Aqua Elya reads sensors (flow rate, pH, EC, water temperature, reservoir levels) and captures a webcam image of the crops. It sends everything to Gemma 4, which uses **native function calling** to make SCADA decisions:

```
Gemma reads:  Flow=3.15 L/min (below 3.5 target), pH=6.0, Temp=70F
Gemma calls:  no_action("All nominal. Flow slightly below target — monitoring for clog.")
Gemma calls:  log_observation("Flow trending 10% below target", category="trend")
```

That's not a threshold alarm. Gemma *noticed* the flow was drifting and proactively flagged it before it became a problem. A PLC wouldn't catch that until flow dropped below the alarm setpoint.

The function calling IS the control system. `set_pump()` turns the pump on or off. `alert_farmer()` sends a plain-language message. `adjust_flow()` changes the target. Gemma 4's built-in tool use replaces ladder logic with natural language reasoning.

## Dual-Brain Architecture: The Innovation

Most entries will use one model. We use **two Gemma 4 models doing different cognitive work on the same laptop**:

**Fast Brain (Gemma 4 E4B on GPU, ~25 seconds):** Real-time SCADA decisions. Should the pump be on? Is this flow rate dangerous? Is the reservoir about to run dry? Reflexive, safety-critical.

**Deep Brain (Gemma 4 26B MoE on CPU, ~2 minutes):** Shift-level trend analysis. Reviews accumulated sensor CSV data and produces agronomist-quality reports.

Here's what the 26B analyst actually produced from our sensor data:

> **Trends:** Aggressive pH upward drift (6.06→6.27). EC declining (1.5→1.34) correlating with pH rise. Flow instability with dip to 2.99 L/min.
>
> **Predictions:** pH will exceed 6.5 threshold within 60 minutes. EC will drop below 1.2 mS/cm within 2 hours.
>
> **URGENT:** Extreme pH spike detected. Verify pH dosing pump is not stuck on.

That's a shift supervisor reading trend charts — except it costs nothing and never sleeps.

## Multimodal: Gemma Sees the Crops

A USB webcam captures images of the NFT channels. Gemma 4 receives sensor data AND the image simultaneously:

> *"Flow declining. Water temp rising. Here is the crop image."*
> Gemma: "Leaves showing early wilt stress. Flow decline correlates with visual evidence. Activating pump. Recommend checking inlet filter."

No separate vision model. Gemma 4 natively fuses sensor readings with visual crop assessment.

## Why Offline Matters More Than Anything

The most important feature is what's **missing**: a cloud requirement.

Every cloud-based AgTech platform assumes reliable internet. That excludes 2.6 billion people without internet access, anyone with metered data, and every remote agricultural region and conflict zone on Earth.

Aqua Elya runs **100% offline**. The laptop is the server, the model, and the controller. WiFi only covers the 10-foot gap between the ESP32 sensor hub and the laptop. No subscription. No API costs. No data leaving the farm.

## Safety: AI Failure Cannot Kill Crops

If Gemma crashes, the system falls back to **hardcoded SCADA rules**:
- Reservoir < 0.5 gal → Shut pump off (never run dry)
- Flow < 1.0 L/min with pump on → Alert critical (clog detected)
- Water temp > 80F → Alert critical (root rot risk)

The AI makes better decisions, but the failsafe keeps crops alive without it.

## Architecture & Deployment Status

**The software is real and runs end-to-end.** Every Gemma output, every function call,
every analyst report shown above is from the actual model running locally — not
mocked, not edited. The full dual-brain control loop executes on a single laptop:
- **Gemma 4 E4B** on Ollama (RTX 4070 laptop, 8GB VRAM)
- **Gemma 4 26B MoE** on CPU (96GB DDR5 system RAM)
- ~1,390 lines of Python + ESP32 firmware, all open-source

**The sensor input is currently stubbed.** The hardware deployment on my actual
108-cell NFT hydroponic system in Houma, Louisiana is the active next phase:
- 108-cell PVC NFT channels — built, growing crops today
- Two aerated 5-gallon reservoirs — built, running
- ~$85 sensor kit (flow meter, pH, EC, temp, level, relay, webcam) — BOM finalized, being assembled
- ESP32 firmware — written, in `esp32_firmware/`, awaiting flash

This submission is for the architecture and the integration pattern. The Gemma 4
function-calling model that replaces ladder logic — that's the contribution.
The same $85 kit, once deployed, works in Nairobi, Za'atari, or Detroit.

## The Numbers

| Metric | Traditional SCADA | Aqua Elya |
|--------|-------------------|-----------|
| Hardware cost | $50,000+ | $85 sensors + used laptop |
| Software license | $5,000+/year | Free (Apache 2.0) |
| Internet required | Usually | Never |
| Languages | English config menus | Any language Gemma speaks |
| Setup time | Days (integrator) | Minutes (git clone + pip install) |
| Decision quality | Fixed thresholds | Contextual reasoning + trends |
| Visual monitoring | Separate camera system | Built into same model |

## Impact Potential

**Global Resilience**: NFT hydroponics + AI monitoring = food production in water-scarce regions with zero internet dependency. The 90% water savings from hydroponics plus AI-timed pump control (Gemma decides when to circulate based on conditions, not a timer) reduces waste another 30-50%.

**Digital Equity**: A $285 total investment (used laptop + sensors) gives any farmer worldwide the same monitoring intelligence that costs Fortune 500 agricultural companies $50,000+ per installation. No internet, no subscription, no English required.

**Education**: Students can clone this repo, run it with simulated sensors in 2 minutes, and learn SCADA, AI, hydroponics, and function calling simultaneously. The code is 1,390 lines of readable Python.

## Try It

```bash
git clone https://github.com/Scottcjn/aqua-sophia.git
cd aqua-sophia
pip install requests
ollama pull gemma4:e4b
python3 scada_loop.py --fast --once    # See Gemma make a SCADA decision
python3 analyst.py --hours 1           # See 26B analyze trends
```

No hardware needed. Stub sensors simulate a realistic NFT system with drift and failure events.

## About

Built by Scott Boudreaux at Elyan Labs, Houma, Louisiana. SCADA technician by trade, hydroponic gardener by choice. The best technology works where it's needed most — not just where the internet is fastest.

GitHub: https://github.com/Scottcjn/aqua-sophia
