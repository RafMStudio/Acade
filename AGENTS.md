# EduItqan engineering rules

Keep the code small, boring, and correct.

1. Read the complete flow before changing it.
2. Fix shared/root logic once; do not patch individual callers.
3. Academic calculations belong in `src/core.js`, not in UI code.
4. Reuse native browser/Node features before adding a dependency.
5. Do not remove validation, error handling, role gates, accessibility labels, or data-integrity checks to reduce line count.
6. `Combined` is derived from Male + Female and must never become a second source of truth.
7. Only Coordinator-approved reports may feed official PLO/APR/HOD calculations.
8. Portfolio uploads are session-only; do not persist portfolio files.
9. Every non-trivial academic-rule change gets one focused regression test.
10. Run `npm test` before release.
