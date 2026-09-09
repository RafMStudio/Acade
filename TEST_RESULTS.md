# Acadeloop 1.0.1 test results

Verification date: 2026-09-09

Command:

```bash
npm test
```

Result:

```text
Build                                      PASS
Core academic/business-rule tests          23 / 23 PASS
Static/source readability checks           PASS
Branding and seed integrity checks         PASS
Deployment bundle styling regression       PASS
Inline app boot without vendor asset       PASS
Chromium full workflow smoke test           PASS
Uncaught browser runtime exceptions        0
```

The deployment regression specifically recreates the condition behind the user's raw/un-styled screenshot: the auxiliary vendor file is removed and the browser is given only the deployment HTML. The test confirms that Acadeloop CSS is still applied, the hidden app shell remains hidden before sign-in, and the app can sign in and render an Instructor workspace.

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
