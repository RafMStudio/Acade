-- Applied to Supabase project bzqtgcopnnscvacynybl on 2026-09-09.
-- Canonical production schema: Course Report DATA is stored; generated DOCX files are not.
-- See Supabase migration history for the full applied DDL and RLS policies.
-- This repository intentionally keeps the schema contract concise; future changes must be added as new migrations.

comment on table public.course_reports is
  'Canonical Course Report DATA only. Generated DOCX files are never stored; they are regenerated on demand from this data.';
comment on column public.course_reports.data is
  'Structured report data required to regenerate reports, analytics, APR/PLO calculations, and exports. No DOCX/binary payloads.';
