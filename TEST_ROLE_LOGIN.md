# Temporary homepage role login

Hosted test access is enabled by `TEMPORARY_ROLE_LOGIN = true` in `src/backend.js`.
Select HOD, Coordinator, Instructor, APU, or VDAA on the homepage to enter
immediately. System Administrator opens `?login=admin` and requires Supabase
email OTP for `rafedmoha@gmail.com` with an active SystemAdmin profile.
Administrator presets and persisted browser administrator roles are rejected. Sign out to select another role. Existing role
permissions still apply, including read-only APU/VDAA workspaces.

The five test roles are preset sample identities, not Supabase accounts.
The authenticated System Administrator uses live Supabase data. Workspace changes are
saved in browser-local storage; portfolio uploads remain in memory for the current
session. Test mode blocks backend requests, including access to previously stored
Supabase credentials. No live user roles, database policies, or auth accounts change.

To remove hosted test access, set `TEMPORARY_ROLE_LOGIN = false`, run `npm test`,
and deploy the rebuilt output. Hosted pages then use the existing verified email
OTP flow; preset role controls are hidden and local test identities are ignored.
Localhost/file-based development testing remains available.
