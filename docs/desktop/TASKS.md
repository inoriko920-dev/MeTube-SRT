# MeTube-SRT Desktop — Task Queue

## IN PROGRESS

### S08-001 — Desktop repository skeleton and CI foundation

**Owner:** SOL  
**Baseline:** STEP 07 + repository main `70e43f058a2bdb0b9bd25d3a5c9fe6442807ec16`

**In scope**

- create isolated `desktop/` project;
- pin proposed Python/tool dependencies;
- create source-of-truth docs;
- add worker protocol scaffold;
- add unit/contract skeleton tests;
- add lint/type/import/secret checks;
- add Windows desktop CI;
- create UI_01..UI_20 manifest.

**Out of scope**

- final UI implementation;
- live downloader feature wave;
- live Gemini execution;
- deleting/moving legacy web code;
- release publication.

**Acceptance**

- desktop package imports;
- worker protocol tests pass;
- import-linter contracts pass;
- Windows CI passes;
- lockfile generated;
- UI manifest has 20 unique IDs and explicit storage status.

## READY AFTER S08-001

- S09-001 — App shell and navigation from frozen UI using fixture data.
