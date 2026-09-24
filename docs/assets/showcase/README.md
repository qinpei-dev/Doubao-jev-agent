# Controlled Agent Showcase capture

`controlled-agent-showcase.txt` is the verified stdout from `python -m examples.showcase` on v0.3.0. The script runs the real controlled chain with the repository's offline JEV mock and disposable sandbox files. The text capture contains no file contents, API key, run IDs, or local paths.

To record a GIF manually:

1. Open Windows Terminal with a dark theme, about **100 columns × 30 rows** and a readable monospace font.
2. From the repository root, start a screen recording, then run only `python -m examples.showcase`.
3. Keep the final output visible for about 15–20 seconds and stop recording. Trim the pause before the command if needed.
4. Review the recording for private terminal history or overlays before exporting to `docs/assets/controlled-agent-showcase.gif`.

The command itself finishes quickly; the suggested duration is for a readable recording. No GIF was generated automatically because this machine has no reliable terminal capture tool. `ffmpeg` is available, but it alone does not capture Windows Terminal output.
