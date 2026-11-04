# EduItqan

Academic quality management software supporting course quality reports, learning-outcome attainment, KPIs, operational planning and evidence-based continuous improvement.

## Architecture
- Cloudflare Worker and static assets
- HTML, CSS and JavaScript, with dedicated core business logic
- Supabase authentication with verified email one-time codes
- PostgreSQL with row-level security and role-based access

## Build
```sh
npm install
npm test
```

Generated artifacts are written to `dist/`, and production builds deploy via the GitHub workflow.

## Security
Production requires an active authorized account. There is no public registration, demonstration login, shared password or browser-local user provisioning. Keep secrets out of source control.

## Intellectual property
Keep a dated source export and commit record as evidence of software authorship. Respect applicable licences for bundled fonts, libraries, templates and third-party material. See THIRD_PARTY_NOTICES.md.
