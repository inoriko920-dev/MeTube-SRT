# MeTube-SRT Desktop — UI Source of Truth

STEP 05 freezes twenty reference states: UI_01 through UI_20.

Canonical global navigation:

- Unduh
- Antrian
- API Gemini
- Pengaturan

AI Agent is a right-side work panel on relevant screens. Manual download remains
available when Gemini is unavailable.

`UI_REFERENCES/manifest.json` records which Git artifact is authoritative for
each UI ID. Missing repository bytes are an evidence/storage gap, not permission
to redesign the screen.
