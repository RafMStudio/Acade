# Acadeloop 1.2.1 test results

Verification date: 2026-09-10

Commands executed:

```bash
npm run build
npm run test:core
npm run check
npm run test:browser
```

Result:

```text
Build                                      PASS
Core academic/business-rule tests          23 / 23 PASS
Static/source readability checks           PASS
Branding and seed integrity checks         PASS
SystemAdmin role-routing regression        PASS
Deployment bundle styling regression       PASS
Inline app boot without vendor asset       PASS
Chromium full workflow smoke test           PASS
Uncaught browser runtime exceptions        0
```

The SystemAdmin regression verifies that the raw database role `SystemAdmin` is canonicalized to the UI role `System Administrator`, opens the System Administration workspace, and does not expose Instructor Course Report navigation.

The full suite also covers:

- all Male + Female → Combined grade/status counts;
- `20 A+ + 15 A+ = 35 A+`;
- starting/completed student totals;
- weighted Combined CLO results;
- Combined integrity auditing;
- grade inflation thresholds and mandatory explanations;
- CLO below-target flags;
- Coordinator approval before PLO/HOD use;
- semester-specific PLO aggregation;
- student-weighted grade distribution;
- Course Report DOCX generation;
- Course Portfolio ZIP placement;
- role-specific navigation;
- HOD test-user creation/login;
- source guard against large embedded Base64/binary blobs.
