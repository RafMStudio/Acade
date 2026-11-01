-- KPI definitions are HOD-owned. Action plans belong exclusively to the assigned owner.
create table public.kpi_definitions (
 id uuid primary key default gen_random_uuid(),
 program_id uuid not null references public.academic_programs(id),
 code text not null check (length(trim(code)) between 1 and 60),
 name text not null check (length(trim(name)) between 1 and 500),
 unit text not null default '%' check (length(trim(unit)) between 1 and 40),
 owner_category text not null check (owner_category in ('Academic','Quality','Extracurricular','Research','HOD')),
 owner_user_id uuid not null references public.profiles(id),
 owner_name text not null,
 unique(id,program_id)
);
create unique index kpi_definition_code on public.kpi_definitions(program_id,lower(code));
create index kpi_definition_owner on public.kpi_definitions(owner_user_id);
create table public.kpi_years (
 id uuid primary key default gen_random_uuid(),
 program_id uuid not null,
 kpi_id uuid not null,
 year_start integer not null check(year_start between 1900 and 9998),
 internal numeric check(internal between 0 and 1000000000000),
 target numeric check(target between 0 and 1000000000000),
 external numeric check(external between 0 and 1000000000000),
 actual numeric check(actual between 0 and 1000000000000),
 new_target numeric check(new_target between 0 and 1000000000000),
 strengths text not null default '' check(length(strengths)<=10000),
 weaknesses text not null default '' check(length(weaknesses)<=10000),
 comparisons text not null default '' check(length(comparisons)<=10000),
 foreign key(kpi_id,program_id) references public.kpi_definitions(id,program_id),
 unique(kpi_id,year_start)
);
create index kpi_year_program on public.kpi_years(program_id);
create table public.kpi_priorities (
 id uuid primary key default gen_random_uuid(),
 program_id uuid not null,
 kpi_id uuid not null,
 year_start integer not null check(year_start between 1900 and 9998),
 priority text not null check(length(trim(priority)) between 1 and 10000),
 foreign key(kpi_id,program_id) references public.kpi_definitions(id,program_id),
 unique(id,program_id)
);
create index kpi_priority_year on public.kpi_priorities(kpi_id,year_start);
create index kpi_priority_program on public.kpi_priorities(program_id);
create table public.kpi_actions (
 priority_id uuid primary key,
 program_id uuid not null,
 actions text not null default '' check(length(actions)<=10000),
 responsible text not null default '' check(length(responsible)<=500),
 start_date date,
 end_date date,
 target numeric check(target between 0 and 1000000000000),
 foreign key(priority_id,program_id) references public.kpi_priorities(id,program_id),
 check(end_date is null or start_date is null or end_date>=start_date)
);
create index kpi_action_program on public.kpi_actions(program_id);

-- Invoker helpers use existing scoped membership policies and active profiles.
-- Unlike has_program_role alone, these do not grant SystemAdmin an HOD bypass.
create function public.kpi_is_hod(p_program_id uuid) returns boolean
language sql stable security invoker set search_path = '' as $$
 select public.has_program_role(p_program_id,array['HOD'])
 and exists(select 1 from public.profiles where id=(select auth.uid()) and active=true and role='HOD');
$$;
create function public.kpi_can_read(p_program_id uuid) returns boolean
language sql stable security invoker set search_path = '' as $$
 select (public.has_program_role(p_program_id) or public.is_global_supervisor())
 and exists(select 1 from public.profiles where id=(select auth.uid()) and active=true);
$$;
create function public.kpi_owns_priority(p_priority_id uuid) returns boolean
language sql stable security invoker set search_path = '' as $$
 select exists(select 1 from public.kpi_priorities p join public.kpi_definitions k on k.id=p.kpi_id
 where p.id=p_priority_id and k.owner_user_id=(select auth.uid())
 and public.has_program_role(k.program_id)
 and exists(select 1 from public.profiles u where u.id=(select auth.uid()) and u.active=true and u.role in ('HOD','Coordinator','Instructor')));
$$;
revoke all on function public.kpi_is_hod(uuid),public.kpi_can_read(uuid),public.kpi_owns_priority(uuid) from public,anon;
grant execute on function public.kpi_is_hod(uuid),public.kpi_can_read(uuid),public.kpi_owns_priority(uuid) to authenticated;

create function public.kpi_validate_owner() returns trigger
language plpgsql security invoker set search_path = '' as $$
begin
 if not exists(select 1 from public.profiles p join public.program_memberships m on m.user_id=p.id
 where p.id=new.owner_user_id and p.active=true and m.active=true and m.program_id=new.program_id
 and m.role in ('HOD','Coordinator','Instructor') and p.role in ('HOD','Coordinator','Instructor')
 and (new.owner_category<>'HOD' or (p.role='HOD' and m.role='HOD'))) then
 raise exception 'KPI owner must be an active user assigned to this program (HOD category requires an HOD).';
 end if;
 return new;
end;
$$;
revoke all on function public.kpi_validate_owner() from public,anon,authenticated;
create trigger kpi_owner_validation before insert or update on public.kpi_definitions for each row execute function public.kpi_validate_owner();

alter table public.kpi_definitions enable row level security;
alter table public.kpi_years enable row level security;
alter table public.kpi_priorities enable row level security;
alter table public.kpi_actions enable row level security;

create policy kpi_definitions_read on public.kpi_definitions for select to authenticated using(public.kpi_can_read(program_id));
create policy kpi_definitions_create on public.kpi_definitions for insert to authenticated with check(public.kpi_is_hod(program_id));
create policy kpi_definitions_edit on public.kpi_definitions for update to authenticated using(public.kpi_is_hod(program_id)) with check(public.kpi_is_hod(program_id));
create policy kpi_years_read on public.kpi_years for select to authenticated using(public.kpi_can_read(program_id));
create policy kpi_years_create on public.kpi_years for insert to authenticated with check(public.kpi_is_hod(program_id));
create policy kpi_years_edit on public.kpi_years for update to authenticated using(public.kpi_is_hod(program_id)) with check(public.kpi_is_hod(program_id));
create policy kpi_priorities_read on public.kpi_priorities for select to authenticated using(public.kpi_can_read(program_id));
create policy kpi_priorities_create on public.kpi_priorities for insert to authenticated with check(public.kpi_is_hod(program_id));
create policy kpi_priorities_edit on public.kpi_priorities for update to authenticated using(public.kpi_is_hod(program_id)) with check(public.kpi_is_hod(program_id));
create policy kpi_actions_read on public.kpi_actions for select to authenticated using(public.kpi_can_read(program_id));
create policy kpi_actions_create on public.kpi_actions for insert to authenticated with check(public.kpi_owns_priority(priority_id));
create policy kpi_actions_edit on public.kpi_actions for update to authenticated using(public.kpi_owns_priority(priority_id)) with check(public.kpi_owns_priority(priority_id));

revoke all on public.kpi_definitions,public.kpi_years,public.kpi_priorities,public.kpi_actions from anon,authenticated;
grant select,insert on public.kpi_definitions,public.kpi_years,public.kpi_priorities,public.kpi_actions to authenticated;
-- Identity / program / year columns cannot be reassigned on update.
grant update(code,name,unit,owner_category,owner_user_id,owner_name) on public.kpi_definitions to authenticated;
grant update(internal,target,external,actual,new_target,strengths,weaknesses,comparisons) on public.kpi_years to authenticated;
grant update(priority) on public.kpi_priorities to authenticated;
grant update(actions,responsible,start_date,end_date,target) on public.kpi_actions to authenticated;
comment on column public.kpi_years.internal is 'Manual fallback only. Effective internal benchmark is always previous year actual when present, computed by the shared KPI core.';
