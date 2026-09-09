# Changelog

## 1.0.1 — resilient deployment bundle

- Fixed the raw/un-styled deployment failure shown when external `src/` assets were missing.
- Inlined Acadeloop-authored CSS, core rules, seed data, and app JavaScript into deployment `index.html`.
- Kept editable source separately in `index.source.html` and `src/`.
- Kept JSZip as a separate third-party vendor asset and the Course Report DOCX as a normal binary template.
- Added a regression browser test proving the page remains styled and interactive even when the vendor asset is absent.
- Added clearer export errors when JSZip or the Word template is missing.
- Fixed the Generate DOCX button so it is always re-enabled after an export error.
- Simplified the Namecheap deployment output to four required paths.
- Preserved all Combined, grade-inflation, CLO-gap, approval, PLO, dashboard, and Course Portfolio rules.

## 1.0.0 — Acadeloop domain-ready readable source

- Rebranded QualiFlow to Acadeloop.
- Removed embedded DOCX Base64 data.
- Added readable source structure, external Word template, tests, and Namecheap guidance.
