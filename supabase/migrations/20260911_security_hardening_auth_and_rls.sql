-- Security hardening applied to production on 2026-09-11.
-- Keeps privileged implementations out of the exposed public schema,
-- removes legacy cross-program policies, and narrows Data API grants.

create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

create or replace function private.is_system_admin_impl()
returns boolean
language sql
stable
security definer
set search_path = public, pg_catalog
as $$
  select exists(
    select 1 from public.profiles
    where id=(select auth.uid()) and active=true and role='SystemAdmin'
  );
$$;

create or replace function private.has_program_role_impl(
  p_program_id uuid,
  p_roles text[] default array['HOD','Coordinator','Instructor']::text[]
)
returns boolean
language sql
stable
security definer
set search_path = public, pg_catalog
as $$
  select private.is_system_admin_impl() or exists(
    select 1 from public.program_memberships
    where program_id=p_program_id
      and user_id=(select auth.uid())
      and active=true
      and role=any(p_roles)
  );
$$;

revoke all on function private.is_system_admin_impl() from public, anon;
revoke all on function private.has_program_role_impl(uuid,text[]) from public, anon;
grant execute on function private.is_system_admin_impl() to authenticated;
grant execute on function private.has_program_role_impl(uuid,text[]) to authenticated;

create or replace function public.is_system_admin()
returns boolean
language sql
stable
security invoker
set search_path = public, private, pg_catalog
as $$ select private.is_system_admin_impl(); $$;

create or replace function public.has_program_role(
  p_program_id uuid,
  p_roles text[] default array['HOD','Coordinator','Instructor']::text[]
)
returns boolean
language sql
stable
security invoker
set search_path = public, private, pg_catalog
as $$ select private.has_program_role_impl(p_program_id,p_roles); $$;

revoke execute on function public.is_system_admin() from public, anon;
revoke execute on function public.has_program_role(uuid,text[]) from public, anon;
grant execute on function public.is_system_admin() to authenticated;
grant execute on function public.has_program_role(uuid,text[]) to authenticated;

-- Remove legacy role-only policies that could broaden writes across programs.
drop policy if exists operational_quality_delete on public.operational_plans;
drop policy if exists operational_quality_insert on public.operational_plans;
drop policy if exists operational_quality_update on public.operational_plans;

-- Least-privilege Data API grants.
revoke all privileges on all tables in schema public from anon;
revoke truncate, references, trigger on all tables in schema public from authenticated;

grant select on public.academic_programs, public.annual_program_reports,
  public.audit_log, public.course_report_history, public.course_reports,
  public.courses, public.operational_plans, public.plos, public.profiles,
  public.program_memberships, public.program_settings, public.project_keepalive
  to authenticated;

grant insert, update, delete on public.academic_programs,
  public.annual_program_reports, public.course_reports, public.courses,
  public.operational_plans, public.plos, public.program_memberships,
  public.program_settings to authenticated;

revoke insert, update, delete on public.audit_log, public.course_report_history,
  public.profiles, public.project_keepalive from authenticated;

create or replace function private.submit_course_report_impl(p_report_id uuid)
returns public.course_reports
language plpgsql
security definer
set search_path = public, private, pg_catalog
as $$
declare v_report public.course_reports;
begin
  select * into v_report from public.course_reports where id=p_report_id for update;
  if v_report.id is null then raise exception 'Report not found'; end if;
  if v_report.program_id is null
     or not private.has_program_role_impl(v_report.program_id,array['Instructor']::text[])
     or v_report.instructor_id<>(select auth.uid())
  then raise exception 'Not authorized'; end if;
  if v_report.status not in ('Draft','Returned for Revision')
  then raise exception 'Report cannot be submitted from current status'; end if;

  update public.course_reports
  set status='Awaiting Quality Approval', submitted_at=now(), return_reason=null,
      version=version+1
  where id=p_report_id returning * into v_report;

  insert into public.course_report_history(report_id,actor_id,action)
  values(p_report_id,(select auth.uid()),'submitted');

  insert into public.audit_log(actor_id,action,entity_type,entity_id,details)
  values((select auth.uid()),'submit','course_report',p_report_id::text,
         jsonb_build_object('program_id',v_report.program_id));
  return v_report;
end;$$;

create or replace function private.review_course_report_impl(
  p_report_id uuid,
  p_decision text,
  p_reason text default null
)
returns public.course_reports
language plpgsql
security definer
set search_path = public, private, pg_catalog
as $$
declare v_report public.course_reports; v_action text;
begin
  if p_decision not in ('approve','return') then raise exception 'Decision must be approve or return'; end if;
  if p_decision='return' and nullif(trim(coalesce(p_reason,'')),'') is null
  then raise exception 'A return reason is required'; end if;

  select * into v_report from public.course_reports where id=p_report_id for update;
  if v_report.id is null then raise exception 'Report not found'; end if;
  if v_report.program_id is null
     or not private.has_program_role_impl(v_report.program_id,array['Coordinator']::text[])
  then raise exception 'Only a Coordinator assigned to this program can review reports'; end if;
  if v_report.status<>'Awaiting Quality Approval'
  then raise exception 'Report is not awaiting quality approval'; end if;

  if p_decision='approve' then
    update public.course_reports
    set status='Approved', reviewed_by=(select auth.uid()), approved_at=now(),
        return_reason=null, version=version+1
    where id=p_report_id returning * into v_report;
    v_action:='approved';
  else
    update public.course_reports
    set status='Returned for Revision', reviewed_by=(select auth.uid()), approved_at=null,
        return_reason=trim(p_reason), version=version+1
    where id=p_report_id returning * into v_report;
    v_action:='returned';
  end if;

  insert into public.course_report_history(report_id,actor_id,action,reason)
  values(p_report_id,(select auth.uid()),v_action,
         case when v_action='returned' then trim(p_reason) else null end);

  insert into public.audit_log(actor_id,action,entity_type,entity_id,details)
  values((select auth.uid()),v_action,'course_report',p_report_id::text,
         jsonb_build_object('program_id',v_report.program_id,'reason',p_reason));
  return v_report;
end;$$;

revoke all on function private.submit_course_report_impl(uuid) from public, anon;
revoke all on function private.review_course_report_impl(uuid,text,text) from public, anon;
grant execute on function private.submit_course_report_impl(uuid) to authenticated;
grant execute on function private.review_course_report_impl(uuid,text,text) to authenticated;

create or replace function public.submit_course_report(p_report_id uuid)
returns public.course_reports
language sql
security invoker
set search_path = public, private, pg_catalog
as $$ select private.submit_course_report_impl(p_report_id); $$;

create or replace function public.review_course_report(
  p_report_id uuid,
  p_decision text,
  p_reason text default null
)
returns public.course_reports
language sql
security invoker
set search_path = public, private, pg_catalog
as $$ select private.review_course_report_impl(p_report_id,p_decision,p_reason); $$;

revoke execute on function public.submit_course_report(uuid) from public, anon;
revoke execute on function public.review_course_report(uuid,text,text) from public, anon;
grant execute on function public.submit_course_report(uuid) to authenticated;
grant execute on function public.review_course_report(uuid,text,text) to authenticated;

alter default privileges in schema public revoke execute on functions from public, anon;
