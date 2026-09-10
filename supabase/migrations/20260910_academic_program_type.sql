alter table public.academic_programs
  add column if not exists program_type text not null default 'Bachelor';

alter table public.academic_programs
  drop constraint if exists academic_programs_program_type_check;

alter table public.academic_programs
  add constraint academic_programs_program_type_check
  check (program_type in ('Diploma', 'Bachelor'));
