# Shared code

`ragcore` is copied verbatim from BridgeBot (`bridgebot/ragcore/`). It is shared code, not a
dependency: there is no cross-repo import, and both copies are tested in their own repo.
When a fix lands in one copy, copy the folder again (all imports inside are relative).
