# Supabase production integration

Acadeloop production uses Supabase for authentication and data persistence.

## Data rule

Course Report DOCX files are **not stored**. `public.course_reports.data` is the canonical structured source. DOCX files are generated on demand from that data and `templates/Course_Report_Placeholder.docx`.

Course Portfolio uploads remain session-only browser `File` objects and are not uploaded to Supabase.

## Authentication

- No public registration.
- Email OTP only.
- `shouldCreateUser/create_user` is disabled in the browser request.
- HOD creates Instructor/Coordinator accounts through the authenticated `admin-create-user` Edge Function.
- Roles: HOD, Coordinator, Instructor.

## Backup

The HOD Users page exposes **Backup & Export Data (.xlsx)**. The authenticated `export-backup-xlsx` Edge Function creates one Excel workbook with Users, Program Settings, Courses, PLOs, Course Reports, Report History, APR Data, Operational Plans, Audit Log, and Backup Info sheets.

## Required Supabase Auth dashboard settings

The Supabase Management connector used during implementation does not expose hosted Auth configuration writes. In Supabase Dashboard set:

1. Authentication → URL Configuration → Site URL = `https://acadeloop.com`
2. Authentication → Email Templates → Magic Link → include `{{ .Token }}` so the email contains the six-digit OTP.

No service-role key belongs in this repository or in browser JavaScript.


## System administration

`rafedmoha@gmail.com` is the bootstrap System Administrator. `SystemAdmin` is a global role and is not tied to one program. Academic program roles are stored in `program_memberships`: HOD, Coordinator, and Instructor.

The System Administrator can open/close academic programs, assign HODs and other users, deactivate/reactivate users, and export the entire database to XLSX. HOD exports are limited to their program.

Course Report DOCX output is generated on demand from structured `course_reports.data` and is never persisted.
