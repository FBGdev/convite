-- Novas respostas podem incluir ate seis acompanhantes, com nome de cada um.
-- As colunas de esposa e filhos continuam disponiveis para registros antigos.
alter table public.rsvps
  add column companion_names text[] not null default '{}',
  add constraint rsvps_companion_names_limit check (cardinality(companion_names) <= 6),
  add constraint rsvps_companion_names_only_when_attending check (attending or cardinality(companion_names) = 0),
  add constraint rsvps_companion_count_matches_names check (
    cardinality(companion_names) = 0 or
    (companions = cardinality(companion_names) and children = 0)
  );
