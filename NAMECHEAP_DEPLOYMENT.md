# Deploy Acadeloop.com — v1.0.1

## Why the previous page looked broken

The raw page in the screenshot means the browser received `index.html` but did not receive the old external CSS/JavaScript files. Without CSS, elements marked `hidden` were visible and the browser fell back to default HTML styling.

Acadeloop v1.0.1 fixes that by putting Acadeloop's own CSS and application code directly in the deployment `index.html`. The page no longer depends on a `src/` folder to render correctly.

## Namecheap Shared Hosting / cPanel

1. Open **cPanel → File Manager**.
2. Open the document root for `Acadeloop.com` (often `public_html`, or the addon-domain folder shown by cPanel).
3. Remove/rename the previous Acadeloop `index.html` so an old cached copy is not accidentally left in place.
4. Upload the **contents** of the v1.0.1 deployment ZIP directly into that document root.
5. Confirm these exact paths exist:

```text
/index.html
/vendor/jszip.min.js
/templates/Course_Report_Placeholder.docx
/robots.txt
```

Do **not** upload a containing folder such as `Acadeloop_Namecheap_Deploy_v1_0_1/` unless that folder itself is configured as the domain document root.

## After upload

Open:

```text
https://acadeloop.com/
```

Then force-refresh once:

- Windows: `Ctrl + F5`
- macOS: `Cmd + Shift + R`

If you use a CDN/cache layer, purge it as well.

## Quick checks

The login page should immediately have the modern Acadeloop styling. You should **not** see the sign-in screen and the main dashboard at the same time.

For export features, these URLs should also resolve:

```text
https://acadeloop.com/vendor/jszip.min.js
https://acadeloop.com/templates/Course_Report_Placeholder.docx
```

The first will display minified third-party JavaScript. The second should download/open the Word template. If either is missing, normal Acadeloop screens still render, but export will show a specific missing-component/template error.

## If the raw page still appears

That means the browser is not receiving the new v1.0.1 `index.html`. Check, in order:

1. the domain points to the folder where the new `index.html` was uploaded;
2. there is not another `index.html` in a higher-priority document root;
3. the ZIP was extracted rather than merely stored on the server;
4. browser/CDN cache was cleared;
5. the page source contains `Acadeloop deployment bundle` near the top.

## Current testing limitation

This release still uses preset test accounts and browser-local storage. Before real institutional use, replace it with the planned HOD-managed server-side user directory, email one-time-code authentication, shared database, server-side authorization, audit logging, and backups.
