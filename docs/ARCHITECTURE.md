# ToolTrust Architecture

The platform separates four concerns:
1. **Tool contract review** — can an agent understand the interface?
2. **Risk and policy** — what kind of side effect can occur, and who must approve it?
3. **Argument/permission validation** — are the inputs and permissions sufficient?
4. **Replay** — show the exact decision path without touching an external system.

The result is an inspectable human-in-the-loop boundary rather than a hidden autonomous action.
