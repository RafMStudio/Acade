-- Institution-wide read-only supervisory roles for APU and VDAA.
-- Applied to production on 2026-09-16.

alter table public.profiles drop constraint if exists profiles_role_check;
alter table public.profiles add constraint profiles_role_check
  check (role = any (array['SystemAdmin'::text,'HOD'::text,'Coordinator'::text,'Instructor'::text,'APU'::text,'VDAA'::text]));

create or replace function private.is_global_supervisor_impl()
returns boolean
language sql
stable
security definer
set search_path = public, pg_catalog
as $$
  select exists (
    select 1
    from public.profiles
    where id = (select auth.uid())
      and active = true
      and role in ('APU','VDAA')
  );
$$;

revoke all on function private.is_global_supervisor_impl() from public, anon;
grant execute on function private.is_global_supervisor_impl() to authenticated;

create or replace function public.is_global_supervisor()
returns boolean
language sql
stable
security invoker
set search_path = public, private, pg_catalog
as $$ select private.is_global_supervisor_impl(); $$;

revoke execute on function public.is_global_supervisor() from public, anon;
grant execute on function public.is_global_supervisor() to authenticated;

drop policy if exists academic_programs_select on public.academic_programs;
create policy academic_programs_select on public.academic_programs
for select to authenticated
using (is_system_admin() or is_global_supervisor() or has_program_role(id));

drop policy if exists apr_select on public.annual_program_reports;
create policy apr_select on public.annual_program_reports
for select to authenticated
using (program_id is not null and (is_global_supervisor() or has_program_role(program_id)));

drop policy if exists audit_select on public.audit_log;
create policy audit_select on public.audit_log
for select to authenticated
using (
  is_system_admin() or is_global_supervisor() or exists (
    select 1 from public.program_memberships m
    where m.user_id=(select auth.uid())
      and m.role='HOD' and m.active=true
      and ((audit_log.details->>'program_id')::uuid = m.program_id)
  )
);

drop policy if exists history_select on public.course_report_history;
create policy history_select on public.course_report_history
for select to authenticated
using (
  is_system_admin() or is_global_supervisor() or exists (
    select 1 from public.course_reports r
    where r.id=course_report_history.report_id
  )
);

drop policy if exists course_reports_select on public.course_reports;
create policy course_reports_select on public.course_reports
for select to authenticated
using (
  program_id is not null and (
    is_system_admin()
    or is_global_supervisor()
    or (has_program_role(program_id,array['Instructor']::text[]) and instructor_id=(select auth.uid()))
    or (has_program_role(program_id,array['Coordinator']::text[]) and status<>'Draft')
    or (has_program_role(program_id,array['HOD']::text[]) and status='Approved')
  )
);

drop policy if exists courses_select on public.courses;
create policy courses_select on public.courses
for select to authenticated
using (program_id is not null and (is_global_supervisor() or has_program_role(program_id)));

drop policy if exists operational_select on public.operational_plans;
create policy operational_select on public.operational_plans
for select to authenticated
using (program_id is not null and (is_global_supervisor() or has_program_role(program_id)));

drop policy if exists plos_select on public.plos;
create policy plos_select on public.plos
for select to authenticated
using (program_id is not null and (is_global_supervisor() or has_program_role(program_id)));

drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles
for select to authenticated
using (
  id=(select auth.uid())
  or is_system_admin()
  or is_global_supervisor()
  or exists (
    select 1
    from public.program_memberships me
    join public.program_memberships target on target.program_id=me.program_id
    where me.user_id=(select auth.uid())
      and me.role='HOD' and me.active=true
      and target.user_id=profiles.id and target.active=true
  )
);

drop policy if exists memberships_select on public.program_memberships;
create policy memberships_select on public.program_memberships
for select to authenticated
using (is_system_admin() or is_global_supervisor() or user_id=(select auth.uid()) or has_program_role(program_id,array['HOD']::text[]));

drop policy if exists settings_select on public.program_settings;
create policy settings_select on public.program_settings
for select to authenticated
using (program_id is not null and (is_global_supervisor() or has_program_role(program_id)));

-- Deliberately no APU/VDAA write policy. Existing INSERT/UPDATE/DELETE/ALL
-- policies remain limited to SystemAdmin/HOD/Coordinator/Instructor workflows.