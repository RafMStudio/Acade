alter table public.profiles
  add column if not exists title_prefix text;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'profiles_title_prefix_check'
      and conrelid = 'public.profiles'::regclass
  ) then
    alter table public.profiles
      add constraint profiles_title_prefix_check
      check (title_prefix is null or title_prefix in ('Mr.', 'Mrs.', 'Dr.'));
  end if;
end
$$;
