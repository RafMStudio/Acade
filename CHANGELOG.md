# Changelog

### 1.2.3 — User prefix and admin entry controls
- Replaced the authorized-user prefix `Mrs.` with `Ms.`; allowed prefixes are now Mr., Ms., and Dr.
- System Administrator can type the academic program code/name directly when assigning a user, with existing open programs offered as suggestions.
- System Administrator can type the department directly; matching program selection can auto-fill its department while remaining editable.
- Added a migration that converts any legacy `Mrs.` prefix to `Ms.` and updates the database constraint.


## 1.2.2
- Added a required professional prefix selector (Mr., Mrs., Dr.) when adding or assigning authorized users.
- Persisted the prefix in Supabase profiles and display it in the authorized-user directory.

## 1.2.1
- Fixed SystemAdmin authentication routing so the database role `SystemAdmin` always opens the System Administration workspace instead of ever falling back to Instructor.
- Canonicalized HOD/SystemAdmin UI roles and made the authenticated Supabase role overwrite stale seed/browser workspace state.
- Added regression checks for raw `SystemAdmin` role handling.

## 1.2.0 — System administration & multi-program architecture
- Added global `SystemAdmin` role above HOD.
- Bootstrapped `rafedmoha@gmail.com` as the first System Administrator.
- Added isolated academic program workspaces with Open/Closed status.
- Added program memberships for HOD, Coordinator, and Instructor.
- System Administrator can create programs, appoint HODs, manage users, and export a whole-system Excel backup.
- HOD remains scoped to its assigned program and can manage its Coordinator/Instructor users.
- Course Reports remain data-only in Supabase; generated DOCX files are never stored.
- Added safe email-auth redirect session handling so default Supabase magic-link email works as a fallback to six-digit OTP.
- Updated backup export to include Academic Programs and Program Memberships and to support system-wide or program-scoped backups.

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

## 1.1.0 — Supabase production integration
- Supabase email OTP production auth; preset test users only in local/test mode.
- Course Report structured data persisted to Supabase; generated DOCX remains on-demand only.
- HOD user creation via protected Edge Function.
- HOD full Excel backup export via protected Edge Function.
- RLS-backed Instructor → Coordinator → HOD workflow.
- Cloudflare Worker deployment config retained for acadeloop.com.
## 1.2.2
- Added a required professional prefix selector (Mr., Mrs., Dr.) when adding or assigning authorized users.
- Persisted the prefix in Supabase profiles and display it in the authorized-user directory.

## 1.2.1
- Fixed SystemAdmin authentication routing so the database role `SystemAdmin` always opens the System Administration workspace instead of ever falling back to Instructor.
- Canonicalized HOD/SystemAdmin UI roles and made the authenticated Supabase role overwrite stale seed/browser workspace state.
- Added regression checks for raw `SystemAdmin` role handling.

## 1.2.0 — System administration & multi-program architecture
- Added global `SystemAdmin` role above HOD.
- Bootstrapped `rafedmoha@gmail.com` as the first System Administrator.
- Added isolated academic program workspaces with Open/Closed status.
- Added program memberships for HOD, Coordinator, and Instructor.
- System Administrator can create programs, appoint HODs, manage users, and export a whole-system Excel backup.
- HOD remains scoped to its assigned program and can manage its Coordinator/Instructor users.
- Course Reports remain data-only in Supabase; generated DOCX files are never stored.
- Added safe email-auth redirect session handling so default Supabase magic-link email works as a fallback to six-digit OTP.
- Updated backup export to include Academic Programs and Program Memberships and to support system-wide or program-scoped backups.

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

## 1.1.0 — Supabase production integration
- Supabase email OTP production auth; preset test users only in local/test mode.
- Course Report structured data persisted to Supabase; generated DOCX remains on-demand only.
- HOD user creation via protected Edge Function.
- HOD full Excel backup export via protected Edge Function.
- RLS-backed Instructor → Coordinator → HOD workflow.
- Cloudflare Worker deployment config retained for acadeloop.com.
