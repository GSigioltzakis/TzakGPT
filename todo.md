# Security Update & Bug Fix — Plan

## Complete
- [x] Read entire codebase for analysis
- [x] Create plan (this file)
- [x] **CRITICAL**: API key leaked — flagged; user must rotate manually
- [x] **HIGH**: Path traversal in /save and /load → `_sanitize_filename()` added
- [x] **HIGH**: No API timeout → `httpx.Timeout(60.0, connect=15.0)` added
- [x] **MEDIUM**: Token thresholds 1.5M/3M → 300K/600K
- [x] **MEDIUM**: max_iterations 100 → 25
- [x] **MEDIUM**: Sliding window breaks on tool call messages → fixed
- [x] **MEDIUM**: Double bell in agent_loop() → removed duplicate
- [x] **MEDIUM**: Swallowed errors in `_apply_sliding_window()` → surfaced
- [x] **LOW**: Dead code removed
  - [x] `handle_tool_call()` in main.py
  - [x] `restore_log()` / `restore_tokens()` in session.py
  - [x] `classify_action()` in soul.py
  - [x] `SHELL_ACTIONS` / `FILE_ACTIONS` in soul.py
  - [x] `classify_action` import removed from main.py
- [x] **LOW**: Client reuse → single `_get_client()` with lazy init
- [x] **LOW**: generate_whitepaper.py font path → `matplotlib.font_manager` (cross-platform)
- [x] **LOW**: `!d`/`!f` prefix documented → added to `/help` table
- [x] **NIT**: .gitignore redundant `*.pyc` → removed
- [x] **NIT**: .env.example cleanup

