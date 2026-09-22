-- Execute no SQL Editor do projeto qwrgrogsuxjxcuhmkxjj.
-- O site acessa a tabela somente pelo servidor, usando uma chave secreta.

create table if not exists public.rsvps (
  id bigint generated always as identity primary key,
  full_name text not null check (char_length(full_name) between 3 and 120),
  phone text not null unique check (phone ~ '^[0-9]{10,11}$'),
  attending boolean not null,
  companions smallint not null default 0 check (companions between 0 and 4),
  edit_code_hash char(64) not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint companions_only_when_attending check (attending or companions = 0)
);

alter table public.rsvps enable row level security;
revoke all on public.rsvps from public, anon, authenticated;
grant select, insert, update, delete on public.rsvps to service_role;
grant usage, select on sequence public.rsvps_id_seq to service_role;
