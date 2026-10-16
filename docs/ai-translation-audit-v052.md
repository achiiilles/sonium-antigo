# Sonium AI lyrics translation audit

Vivi Music uses Gemini's OpenAI-compatible chat completions endpoint with a Bearer API key and a JSON array of translated lyric strings. Its response parser handles Markdown and malformed output fallbacks.

Sonium has an Android player host delegating translation to LyricsTranslation. The build applies .github/scripts/patch_ai_lyrics.py before compilation, so the repository host alone does not establish the runtime call path. All build-time patches must be inspected before attributing the failure to this delegation.

The requested fix must preserve lyric timestamps, retrieve the configured Gemini credential at translation time, respect the selected target language, show Traduzindo por IA..., and produce version 0.5.2 (35). No credential may be committed or logged.
