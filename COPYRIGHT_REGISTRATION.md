# EduItqan — Software Copyright Registration Dossier

**Product:** EduItqan  
**Work category:** Computer software and applications  
**Website:** https://eduitqan.com  
**Snapshot date:** 2026-11-04  
**Status:** Pre-submission review; not an ownership certificate

## Description of the software
EduItqan is an academic quality-management platform for institutional continuous improvement. It provides role-based workflows for course reports, course learning outcome assessment, program learning outcome attainment, operational plans, KPIs, quality oversight, evidence organization and report generation.

## Custom implementation — proposed scope of deposited work
The independently authored implementation, to the extent that the applicant can establish legal title to it, includes:

- Application interface and workflow implementation: `index.source.html`, `src/app.js`, `src/home.html`, `src/styles.css`, `src/home.css`, `src/visuals.js`
- Academic calculation and validation logic: `src/core.js`
- Localization and interface dictionaries: `src/i18n.js`, `src/i18n-ar.js`
- Authentication integration and client data access: `src/backend.js`
- Build and validation utilities: `scripts/build.js`, `scripts/check-project.js`
- Database structure and security configuration: `supabase/migrations/`
- Server-side account-management handlers: `supabase/functions/`

## Third-party and potentially externally owned elements
Do **not** claim exclusive authorship of:
- JSZip and its bundled third-party dependencies;
- Readex Pro and its fonts;
- generic academic standards, learning-outcome terminology, accreditation requirements or third-party methodologies;
- the supplied DOCX course report template until its ownership, originality and permission for reuse have been verified;
- any code, graphics, documents or materials created for another party under contractual ownership or work-for-hire terms.

Refer to `THIRD_PARTY_NOTICES.md` and the bundled font licence.

## Security and release state
- Production sign-in uses authorized, verified email one-time codes.
- Browser-local demonstration identities and their shared password have been removed from the current source branch.
- Administrative Edge Functions authorize the caller and check assigned roles.
- Database access is controlled by row-level security.
- Automated source checks are provided through GitHub Actions.
- **Public production release is not certified until Cloudflare deployment succeeds, the domain is tested in a browser and the remaining asset/ownership checks are completed.**

## Evidence to preserve before filing
1. A dated archive of the final source code, including unmodified commit hash.
2. A separate description of individually authored features and source files.
3. A written statement identifying the actual author(s) and copyright owner(s), including employment and contractual transfer arrangements.
4. Permissions and licence evidence for externally sourced code, fonts, document templates and graphics.
5. Screenshots of completed software workflows and an accurate version/release record.
6. Evidence that the proposed deposited work represents a finished work rather than an incomplete draft.

## Registration
Saudi Authority for Intellectual Property: use the service **Registration of a New Work — Computer Software and Applications**. Submit the required filing materials through the official portal and pay applicable fees.

**Important:** The existence of this document or a public repository does not establish copyright ownership, transfer rights, eligibility, or acceptance of registration. Complete author and rights verification before making a legal declaration.

## Pre-filing acceptance criteria
- [ ] Deployed version matches the final repository revision
- [ ] Production authentication and all role permissions verified
- [ ] All institution-specific and personally identifying sample material reviewed
- [ ] Document template ownership resolved or a wholly original template supplied
- [ ] Third-party components clearly excluded from claimed original authorship
- [ ] Applicants, owners and contributor permissions documented
- [ ] Final archival source export prepared and checked
