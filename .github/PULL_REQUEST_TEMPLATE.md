## Ticket
Closes #<issue number> (ticket NN: title)

## What changed
<2 to 5 lines>

## Acceptance boxes proved
- [ ] <box text>: proof (test name or command)

## Checks
- [ ] `python scripts/dev.py ci` passes locally
- [ ] Golden set not lower (`python scripts/dev.py eval --lang <code>`), if answers changed
- [ ] No secrets or real keys; `.env` untouched
- [ ] Licence register updated for any new source
- [ ] Fixtures carry a provenance label
- [ ] Docs, glossary or ADR updated if a decision or term changed
- [ ] Exactly one Alembic head, if there is a migration
- [ ] Label `contract` added, if `packages/contracts/` changed

## Assumptions and risks
<anything the agent decided on its own>

## Screenshots or recordings (UI changes)

## Notes for the reviewer
