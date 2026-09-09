# Acadeloop

Academic program quality management web application for **Acadeloop.com**.

## v1.0.1 deployment fix

The previous deployment could appear as raw, unstyled HTML when `src/styles.css` and the application JavaScript were not uploaded/extracted beside `index.html`. In that failure mode the browser displayed both the sign-in page and the normally hidden app shell at once.

v1.0.1 removes that fragile dependency for the Acadeloop-authored UI:

- `index.html` now contains the Acadeloop CSS, business-rule core, seed data, and app JavaScript inline;
- the UI therefore remains styled and interactive even if the auxiliary source folder is absent;
- JSZip remains a separate third-party vendor file at `vendor/jszip.min.js`;
- the Course Report Word template remains a normal binary file at `templates/Course_Report_Placeholder.docx`;
- no DOCX Base64 blob is embedded in HTML or JavaScript.

The editable source remains separate and readable.

## Project layout

```text
Acadeloop/
├── index.html                         # generated resilient deployment bundle
├── index.source.html                  # readable HTML source shell
├── src/
│   ├── app.js                         # browser UI and workflow orchestration
│   ├── core.js                        # academic/business rules
│   ├── seed.js                        # test/demo data
│   ├── styles.css                     # application styling
│   └── vendor/jszip.min.js            # third-party minified library
├── vendor/jszip.min.js                # deployment copy
├── templates/
│   └── Course_Report_Placeholder.docx # binary Word template
├── reference/
│   └── Course portfolio structure.pdf
├── tests/core.test.js
├── scripts/
│   ├── build.js
│   ├── check-project.js
│   └── browser-smoke.js
├── dist/                              # ready-to-upload output
├── NAMECHEAP_DEPLOYMENT.md
├── ARCHITECTURE.md
└── TEST_RESULTS.md
```

Only the third-party JSZip file is intentionally minified. The Acadeloop-authored source remains readable under `index.source.html` and `src/`.

## Included functionality

- role-specific Instructor, Coordinator, and HOD workspaces;
- S1 / S2 / Summer Course Reports;
- Male / Female / Combined / All reporting;
- deterministic Male + Female → Combined calculations;
- grade inflation detection and mandatory explanation/recommendation;
- CLO actual-vs-target monitoring;
- Coordinator approval gate before PLO/APR/HOD official calculations;
- HOD test-user management;
- generated-only Course Portfolio builder;
- DOCX Course Report and Portfolio ZIP generation;
- PLO attainment, APR, Operational Plan, and quality dashboards.

## Test accounts

| User | Role |
| --- | --- |
| `TestHOD` | Head of Department |
| `TestI` | Instructor |
| `TestQ` | Coordinator |
| `TestI2` | Instructor |

This is still a browser-local **testing build**. Do not use real institutional data yet.

## Build and test

```bash
npm run build
npm test
```

`npm run build` generates `dist/`. `npm test` verifies the academic rules, source/build integrity, the deployment-bundle regression that prevents the raw/un-styled page, and the full Chromium workflow.

## Deploy

Upload the **contents of `dist/`** to the document root for Acadeloop.com. See `NAMECHEAP_DEPLOYMENT.md`.

The minimum deployment is intentionally small:

```text
index.html
vendor/jszip.min.js
templates/Course_Report_Placeholder.docx
robots.txt
```

If only `index.html` is present, Acadeloop will still render and its normal screens will work, but DOCX/ZIP export requires the vendor and template files above.
