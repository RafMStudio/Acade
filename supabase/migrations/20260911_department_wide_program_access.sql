alter table public.profiles
  add column if not exists limit_program_access boolean not null default false;

alter table public.academic_programs
  alter column current_academic_year drop default,
  alter column current_academic_year drop not null;

update public.academic_programs set current_academic_year = null;

insert into public.program_memberships (program_id, user_id, role, active, created_by)
select ap.id, p.id, p.role, p.active, p.created_by
from public.profiles p join public.academic_programs ap on ap.department = p.department
where p.role in ('HOD','Coordinator','Instructor') and p.limit_program_access = false
on conflict (program_id, user_id) do update set role=excluded.role, active=excluded.active;

create or replace function public.sync_department_memberships_for_new_program() returns trigger language plpgsql set search_path=public as $$
begin
 insert into public.program_memberships(program_id,user_id,role,active,created_by)
 select new.id,p.id,p.role,p.active,p.created_by from public.profiles p
 where p.department=new.department and p.role in ('HOD','Coordinator','Instructor') and p.limit_program_access=false
 on conflict(program_id,user_id) do update set role=excluded.role,active=excluded.active;
 return new;
end;$$;
drop trigger if exists academic_programs_sync_department_memberships on public.academic_programs;
create trigger academic_programs_sync_department_memberships after insert on public.academic_programs for each row execute function public.sync_department_memberships_for_new_program();
