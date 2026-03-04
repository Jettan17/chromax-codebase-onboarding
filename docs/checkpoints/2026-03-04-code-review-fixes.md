# Checkpoint: code-review-fixes

Created: 2026-03-04
Git SHA: 7065e1d
Branch: main

## Summary
Applied all Critical and High severity findings from code review.
Phase 1 and Phase 2 fully implemented and verified. Ready for Phase 3.

## Files Changed (since last checkpoint)
- src/chromax/agents/basic.py (modified — prompt injection defense, recursion_limit)
- src/chromax/cli.py (modified — error handling in all commands)
- src/chromax/indexer/chunker.py (modified — removed .env from TEXT_EXTENSIONS)
- src/chromax/indexer/indexer.py (modified — added public query() method)
- src/chromax/tools/github.py (modified — cached GitHub client)
- src/chromax/tools/search.py (modified — uses Indexer.query() public API)

## Test Status
- Unit (chunker, github tools, agent): 28 passed
- Integration (TestIndexer — psf/requests): 4 passed (module-scoped, slow)
- E2E: N/A
- Coverage: ~65% overall (indexer.py covered by excluded integration tests)

## Security Fixes Applied
- CRITICAL: .env no longer indexed (secret leakage prevention)
- CRITICAL: LLM system prompt instructs model to ignore injected instructions in file content
- HIGH: recursion_limit=25 prevents infinite tool-call loops
- HIGH: CLI exits with code 1 on error, prints to stderr
- HIGH: GitHub client cached — no longer instantiated per API call
- HIGH: Indexer._collection no longer accessed outside the class

## Notes
- LLM provider: Groq llama-3.3-70b-versatile (switched from Gemini due to regional quota restriction)
- BadRequestError (tool_use_failed) retry fallback still in place for Groq edge case
- Windows cp1252 encoding fixes in place (SpinnerColumn("line"), no em dashes)
- Next: Phase 3 — multi-agent routing and conversation memory
