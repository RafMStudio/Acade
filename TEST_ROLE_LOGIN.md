# Temporary homepage role login

Hosted test access is enabled by `TEMPORARY_ROLE_LOGIN = true` in `src/backend.js`.
Select System Administrator, HOD, Coordinator, Instructor, APU, or VDAA on the
homepage to enter immediately. Sign out to select another role. Existing role
permissions still apply, including read-only APU/VDAA workspaces.

These are preset sample identities, not Supabase accounts. Workspace changes are
saved in browser-local storage; portfolio uploads remain in memory for the current
session. Test mode blocks backend requests, including access to previously stored
Supabase credentials. No live user roles, database policies, or auth accounts change.

To remove hosted test access, set `TEMPORARY_ROLE_LOGIN = false`, run `npm test`,
and deploy the rebuilt output. Hosted pages then use the existing verified email
OTP flow; preset role controls are hidden and local test identities are ignored.
Localhost/file-based development testing remains available.
