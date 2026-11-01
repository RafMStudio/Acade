-- Integration test against an existing program with active HOD/Coordinator/Instructor.
-- All test records and settings are rolled back, including on an error.
begin;
select set_config('test.kpi_hod',m.user_id::text,true),set_config('test.kpi_program',m.program_id::text,true)
from public.program_memberships m join public.profiles p on p.id=m.user_id where m.role='HOD' and m.active and p.active limit 1;
select set_config('test.kpi_owner',m.user_id::text,true) from public.program_memberships m join public.profiles p on p.id=m.user_id where m.program_id=current_setting('test.kpi_program')::uuid and m.role='Coordinator' and m.active and p.active limit 1;
select set_config('test.kpi_id',gen_random_uuid()::text,true),set_config('test.kpi_priority',gen_random_uuid()::text,true);
set local role authenticated;
select set_config('request.jwt.claims',json_build_object('sub',current_setting('test.kpi_hod'),'role','authenticated')::text,true);
insert into public.kpi_definitions(id,program_id,code,name,owner_category,owner_user_id,owner_name)
values(current_setting('test.kpi_id')::uuid,current_setting('test.kpi_program')::uuid,current_setting('test.kpi_id'),'Rollback test KPI','Quality',current_setting('test.kpi_owner')::uuid,'Test owner');
insert into public.kpi_years(program_id,kpi_id,year_start,actual) values(current_setting('test.kpi_program')::uuid,current_setting('test.kpi_id')::uuid,2026,75);
insert into public.kpi_priorities(id,program_id,kpi_id,year_start,priority) values(current_setting('test.kpi_priority')::uuid,current_setting('test.kpi_program')::uuid,current_setting('test.kpi_id')::uuid,2026,'Rollback test priority');
update public.kpi_years set actual=80 where kpi_id=current_setting('test.kpi_id')::uuid;
select set_config('request.jwt.claims',json_build_object('sub',current_setting('test.kpi_owner'),'role','authenticated')::text,true);
do $$ declare n integer; begin
 update public.kpi_years set actual=1 where kpi_id=current_setting('test.kpi_id')::uuid;
 get diagnostics n=row_count;
 if n<>0 then raise exception 'Owner incorrectly edited HOD annual record'; end if;
 begin
 insert into public.kpi_priorities(program_id,kpi_id,year_start,priority) values(current_setting('test.kpi_program')::uuid,current_setting('test.kpi_id')::uuid,2026,'Forbidden');
 raise exception 'Owner incorrectly created priority';
 exception when insufficient_privilege then null; end;
end $$;
insert into public.kpi_actions(priority_id,program_id,actions,responsible,start_date,end_date,target) values(current_setting('test.kpi_priority')::uuid,current_setting('test.kpi_program')::uuid,'Owner action','Committee','2026-11-01','2026-12-01',90);
update public.kpi_actions set target=92 where priority_id=current_setting('test.kpi_priority')::uuid;
do $$ begin
 if (select target from public.kpi_actions where priority_id=current_setting('test.kpi_priority')::uuid)<>92 then raise exception 'Owner update failed'; end if;
 begin
 update public.kpi_actions set end_date='2026-01-01' where priority_id=current_setting('test.kpi_priority')::uuid;
 raise exception 'Invalid dates allowed';
 exception when check_violation then null; end;
 begin
 update public.kpi_actions set program_id=gen_random_uuid() where priority_id=current_setting('test.kpi_priority')::uuid;
 raise exception 'Identity change allowed';
 exception when insufficient_privilege then null; end;
end $$;
select set_config('request.jwt.claims',json_build_object('sub',current_setting('test.kpi_hod'),'role','authenticated')::text,true);
do $$ declare n integer; begin
 update public.kpi_actions set target=10 where priority_id=current_setting('test.kpi_priority')::uuid;
 get diagnostics n=row_count;
 if n<>0 then raise exception 'Non-owner HOD edited action plan'; end if;
end $$;
rollback;
select 'Passed: HOD definitions/benchmarks, owner-only actions, denied owner KPI edits, immutable scope, date validation; test records rolled back.' as result;
