# Paradee light assets

Paradee-8M v1.0 by Sahil Mahendrakar. Model and config are vendored from Hugging Face revision `f662642d44c03c17588e4176469c54d462c0b623`. The unmodified browser eSpeak→misaki adapter is from `sahilmahendrakar/paradee` revision `9c8b4d7504cbee7e64de2d0341bb690f0b0ab708`, `web/misaki.js`. See `provenance.json` for file sizes and SHA-256 checksums. Both upstream projects license these artifacts under Apache-2.0; the full license is included in `LICENSE`.

Source: https://huggingface.co/sahilmahendrakar/Paradee-8M-v1.0 and https://github.com/sahilmahendrakar/paradee

Paradee is distilled from hexgrad/Kokoro-82M and supports American English with one voice, `af_heart`. It outputs 24 kHz audio, takes `input_ids` (int64 with boundary zeros, at most 512 ids) and `speed` (float32), and needs the included phoneme spelling conversion. It has no voice style embedding input. It can retain a faint buzz and has pronunciation limitations for numbers, abbreviations and unusual words. This is an optional trial engine, not a default replacement.

The model itself is 9,037,971 bytes. First use also loads the existing shared ONNX Runtime/WASM and eSpeak phonemizer; this is not a 9 MB total first download. No demo-server API or additional credentials are used.
