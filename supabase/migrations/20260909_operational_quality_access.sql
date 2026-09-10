drop policy if exists operational_hod_insert on public.operational_plans;
drop policy if exists operational_hod_update on public.operational_plans;
create policy operational_quality_insert on public.operational_plans for insert to authenticated
  with check (public.current_user_role() in ('HOD','Coordinator'));
create policy operational_quality_update on public.operational_plans for update to authenticated
  using (public.current_user_role() in ('HOD','Coordinator'))
  with check (public.current_user_role() in ('HOD','Coordinator'));
create policy operational_quality_delete on public.operational_plans for delete to authenticated
  using (public.current_user_role() in ('HOD','Coordinator'));
