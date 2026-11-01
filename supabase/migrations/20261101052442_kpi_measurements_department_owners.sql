alter table public.kpi_definitions alter column owner_user_id drop not null;
alter table public.kpi_definitions alter column owner_name set default '';
alter table public.kpi_definitions add column ratio_out_of numeric;
alter table public.kpi_definitions add constraint kpi_measurement_valid check (
 (unit='%' and ratio_out_of is null) or
 (unit='ratio' and ratio_out_of is not null and ratio_out_of>0 and ratio_out_of<=1000000000000)
);
grant update(ratio_out_of) on public.kpi_definitions to authenticated;

-- Global supervision must not bypass department isolation for KPIs.
create or replace function public.kpi_can_read(p_program_id uuid) returns boolean
language sql stable security invoker set search_path = '' as $$
 select (public.has_program_role(p_program_id) or public.is_global_supervisor())
 and exists(select 1 from public.profiles p join public.academic_programs a on a.id=p_program_id
 where p.id=(select auth.uid()) and p.active=true
 and p.role in ('HOD','Coordinator','Instructor','APU','VDAA')
 and nullif(btrim(p.department),'') is not null and btrim(p.department)=btrim(a.department));
$$;
create or replace function public.kpi_is_hod(p_program_id uuid) returns boolean
language sql stable security invoker set search_path = '' as $$
 select public.kpi_can_read(p_program_id) and public.has_program_role(p_program_id,array['HOD'])
 and exists(select 1 from public.profiles where id=(select auth.uid()) and active=true and role='HOD');
$$;
create or replace function public.kpi_owns_priority(p_priority_id uuid) returns boolean
language sql stable security invoker set search_path = '' as $$
 select exists(select 1 from public.kpi_priorities p join public.kpi_definitions k on k.id=p.kpi_id
 where p.id=p_priority_id and k.owner_user_id=(select auth.uid())
 and public.kpi_can_read(k.program_id) and public.has_program_role(k.program_id)
 and exists(select 1 from public.profiles u where u.id=(select auth.uid()) and u.active=true and u.role in ('HOD','Coordinator','Instructor')));
$$;

create or replace function public.kpi_validate_owner() returns trigger
language plpgsql security invoker set search_path = '' as $$
begin
 if tg_op='UPDATE' and (new.unit is distinct from old.unit or new.ratio_out_of is distinct from old.ratio_out_of) then
  if exists(select 1 from public.kpi_years y where y.kpi_id=old.id and
   (y.internal is not null or y.target is not null or y.external is not null or y.actual is not null or y.new_target is not null))
   or exists(select 1 from public.kpi_actions a join public.kpi_priorities p on p.id=a.priority_id where p.kpi_id=old.id and a.target is not null) then
   raise exception 'Measurement is fixed once benchmarks exist, so historical results stay comparable.';
  end if;
 end if;
 -- A category is a valid owner before any person is registered.
 if new.owner_user_id is null then new.owner_name=''; return new; end if;
 if not exists(select 1 from public.profiles p join public.program_memberships m on m.user_id=p.id
 join public.academic_programs a on a.id=m.program_id
 where p.id=new.owner_user_id and p.active=true and m.active=true and m.program_id=new.program_id
 and nullif(btrim(p.department),'') is not null and btrim(p.department)=btrim(a.department)
 and m.role in ('HOD','Coordinator','Instructor') and p.role in ('HOD','Coordinator','Instructor')
 and (new.owner_category<>'HOD' or (p.role='HOD' and m.role='HOD'))) then
 raise exception 'Linked owner must be an active user in this department and program. HOD category requires an HOD.';
 end if;
 return new;
end;
$$;

create function public.kpi_validate_benchmarks() returns trigger
language plpgsql security invoker set search_path = '' as $$
declare measurement text;
begin
 if tg_table_name='kpi_years' then
  select unit into measurement from public.kpi_definitions where id=new.kpi_id;
  if measurement='%' and (new.internal>100 or new.target>100 or new.external>100 or new.actual>100 or new.new_target>100) then
   raise exception 'Percentage benchmarks must be between 0 and 100.';
  end if;
 else
  select k.unit into measurement from public.kpi_definitions k join public.kpi_priorities p on p.kpi_id=k.id where p.id=new.priority_id;
  if measurement='%' and new.target>100 then raise exception 'Percentage benchmarks must be between 0 and 100.'; end if;
 end if;
 return new;
end;
$$;
revoke all on function public.kpi_validate_benchmarks() from public,anon,authenticated;
create trigger kpi_year_measurement before insert or update on public.kpi_years for each row execute function public.kpi_validate_benchmarks();
create trigger kpi_action_measurement before insert or update on public.kpi_actions for each row execute function public.kpi_validate_benchmarks();
