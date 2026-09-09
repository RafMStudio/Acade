# Acadeloop architecture

Acadeloop separates readable source, academic business rules, and deployment concerns.

## Readable source

`index.source.html` is the editable page shell. `src/styles.css`, `src/core.js`, `src/seed.js`, and `src/app.js` are the authored source files.

## Deployment `index.html`

The build script generates a resilient `index.html` by inlining Acadeloop's own CSS and JavaScript. This removes the failure mode where a missing `src/` directory makes the site render as raw browser-default HTML.

The deployment bundle intentionally does **not** embed the Word template. It also keeps the third-party JSZip library separate.

## `src/core.js`

Authoritative DOM-free business-rule layer:

- Male/Female → Combined calculations;
- Combined integrity auditing;
- grade inflation detection;
- CLO target-gap detection;
- pooled grade distribution;
- report validation;
- PLO rollups.

## `src/app.js`

Browser workflow and UI orchestration:

- role-specific screens;
- test login/user directory;
- Course Report forms;
- Coordinator approval;
- generated-only Course Portfolio builder;
- DOCX/ZIP/CSV export;
- browser-local test persistence.

## Export assets

```text
vendor/jszip.min.js
templates/Course_Report_Placeholder.docx
```

Normal application rendering does not depend on either file. Export functions do. If JSZip is unavailable, Acadeloop now shows a specific deployment error instead of leaving the export button disabled.

## Approval invariant

```text
Instructor Draft
  → Awaiting Quality Approval
  → Coordinator Approved
  → PLO / APR / HOD official views / official portfolio generation
```

## Combined invariant

For `sectionMode = all`, Male and Female are the source of truth. Combined data is deterministically recalculated before save, submit, approval, PLO use, and export.

## Current limitation

Authentication and state remain browser-local for testing. Production requires a shared backend, HOD-managed accounts, email OTP, server-side authorization, and durable audit/storage.
