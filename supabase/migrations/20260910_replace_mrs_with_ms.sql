update public.profiles
set title_prefix = 'Ms.'
where title_prefix = 'Mrs.';

alter table public.profiles
  drop constraint if exists profiles_title_prefix_check;

alter table public.profiles
  add constraint profiles_title_prefix_check
  check (title_prefix is null or title_prefix in ('Mr.', 'Ms.', 'Dr.'));
