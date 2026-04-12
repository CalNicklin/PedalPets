# PedalPets

An animated pet pedal for guitar pedalboards. Passes signal transparently,
taps it internally, and animates a sprite on a small screen based on playing
intensity.

## Behaviour

Three states driven by guitar signal RMS:

| State   | Trigger                     | Animation                       |
|---------|-----------------------------|---------------------------------|
| IDLE    | Silence > 3s                | Slow breathing, occasional blink |
| AWAKE   | Signal above low threshold  | Alert, gentle head bob           |
| ROCKING | Signal above high threshold | Headbanging, chaos               |

Transitions use fast attack / slow release (compressor-style envelope) so the
pet doesn't flicker between states on transients.

## Hardware

- ESP32 dev board (ESP32-WROOM-32, CP2102 USB-UART)
- 1.8" ST7735 TFT display, 128x160, SPI
- 125B pedal enclosure (Phase 2)
- 3PDT stomp switch (Phase 2)
- 1/4" input + output jacks (Phase 2)
- USB-C power from pedalboard 5V USB

## Signal path

```
INPUT ─────────────────────────────────── OUTPUT   (true bypass, always live)
           │
           ├── 1MΩ series
           │
          AC-couple (100nF) + 1.65V bias (2x100kΩ divider to 3.3V)
           │
         ESP32 ADC (GPIO 34)
```

- Input impedance ≥1MΩ so tone isn't coloured.
- DC-biased midpoint so negative halves of the audio waveform are readable.
- Signal clamped to 0–3.3V range for ADC safety.

## Pin map (ESP32)

| Function     | GPIO |
|--------------|------|
| Audio ADC in | 34   |
| TFT MOSI     | 23   |
| TFT SCLK     | 18   |
| TFT CS       | 5    |
| TFT DC       | 17   |
| TFT RST      | 4    |
| Sensitivity pot (opt.) | 35 |
| Status LED   | 2    |

## Firmware architecture

FreeRTOS dual-core on ESP32:

- **Core 0** — audio sampling task: reads ADC at ~8kHz, computes rolling RMS
  over ~50ms windows, publishes current level to a shared atomic.
- **Core 1** — animation task: reads level, drives state machine (IDLE/AWAKE/
  ROCKING), renders sprite frames to TFT via TFT_eSPI (double-buffered).

State transitions:

- Level > `HIGH_THRESHOLD` → ROCKING immediately (fast attack).
- Level < `LOW_THRESHOLD` for > `RELEASE_MS` → decay one state down.
- Trimpot on GPIO 35 scales thresholds at runtime.

## Build phases

1. **Phase 1 — bench prototype**: ESP32 + ST7735 + breadboard, audio tap via
   a test wire or headphone jack, sprite animating off signal level.
2. **Phase 2 — enclosed pedal**: 125B enclosure, 3PDT true bypass switch,
   1/4" jacks, buffered signal tap, internal trimpot.
3. **Phase 3 — polish**: multiple pet designs, state-based colour LED, OTA
   firmware updates (maybe).

## BOM (Phase 1, ~£25)

- ESP32 dev board — ~£7
- 1.8" ST7735 TFT module (with header pins!) — ~£6
- ELEGOO breadboard + jumper + resistor + cap kit — ~£13

## Open questions

- Which pet sprite(s) to ship by default?
- Add a BOOT-to-reset button (for mode cycling) on the pedal?
- Is USB-C power enough, or add a barrel-jack 9V option for non-USB boards?
