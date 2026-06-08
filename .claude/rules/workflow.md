# Workflow Rules

## The Development Loop

Every piece of work — no matter how small — must follow this loop:

```
1. TASK    Define what you're building, why it's needed, and what "done" looks like
2. BUILD   Implement the change in the smallest reasonable increment
3. VERIFY  Prove it works: short video clip, photo, or test output
```

**Never** mark a task complete without verification evidence. Arm motion changes especially — a recorded video of the arm executing the new sequence at slow speed is the bare minimum.

---

## Plan Before You Build (Complex Features)

For anything that touches both the Jetson and the Arduino (or any new motion sequence), write a brief plan first:

- What problem does this solve?
- What files will change?
- What's the rollback plan if the new motion damages something?
- What's the verification test?

Only start building after the plan is on paper (or in the chat).

---

## Branch Strategy

| Prefix | When to use |
|---|---|
| `feature/` | New functionality (new bin, new classification mode) |
| `fix/` | Bug fixes |
| `chore/` | Config, tooling, dependency updates |
| `docs/` | Documentation only |
| `calibrate/` | HSV threshold or servo-angle tuning runs |

Branch from `main`. Keep branches short-lived. Merge via Pull Request.

---

## Commit Message Format

```
type: short description (present tense, lowercase)

Examples:
feat: add motion sequence for Bin C (blue)
fix: correct HSV range for green items under fluorescent light
chore: update gh CLI workflow for nightly builds
docs: add wiring diagram for level shifter
calibrate: re-tune base servo angles after arm reassembly
```

**Co-author trailer:** Faaz's NurdleDNA convention is **no** `Co-Authored-By: Claude` trailers on commits. Same convention applies here unless explicitly requested.

---

## Hardware Bring-Up Workflow

Before working on any motion or vision code:
1. Power on the Arduino + servos with a known-good demo sketch. Verify all servos sweep their full range without binding.
2. Power on the Jetson. Verify the camera enumerates (`ls /dev/video*`).
3. Verify the level shifter passes a known signal from Jetson GPIO to Arduino GPIO (set Jetson pin HIGH, read Arduino pin HIGH).
4. **Only then** start integrating.

Skipping these steps means debugging a problem with no idea which side broke it.

---

## Pull Request Checklist

- [ ] Branch is up to date with `main`.
- [ ] No `.env`, secrets, or local config files accidentally staged.
- [ ] If a motion sequence changed, a short video of the arm running it is in the PR description.
- [ ] If HSV thresholds changed, before/after screenshots of the classifier mask are in the PR description.
- [ ] At least one team member has reviewed.
- [ ] CI (if/when added) passes.

---

## Safety Workflow

For any change that affects arm motion:
1. **Slow speed first** — set the global speed scalar to ~0.3 before running the new sequence.
2. **Hand on the E-stop** — physically near the switch during the first run.
3. **One bin at a time** — test each bin's motion in isolation before testing the full sort cycle.
4. **Record the first run** — even if it fails, the video helps debug.

If an arm grinds, stalls, or makes unusual noise: cut power immediately. Investigate before re-energising.
