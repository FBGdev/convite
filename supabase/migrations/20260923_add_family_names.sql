-- Execute antes de publicar o formulário que coleta nomes da esposa e dos filhos.
-- Os registros antigos e suas contagens permanecem intactos.
alter table public.rsvps
  add column wife_name text,
  add column children_names text[] not null default '{}',
  add constraint rsvps_wife_name_length check (wife_name is null or char_length(wife_name) between 2 and 120),
  add constraint rsvps_children_names_limit check (cardinality(children_names) <= 2),
  add constraint rsvps_family_only_when_attending check (attending or (wife_name is null and cardinality(children_names) = 0)),
  add constraint rsvps_wife_count_matches_name check (wife_name is null or companions = 1),
  add constraint rsvps_children_count_matches_names check (cardinality(children_names) = 0 or children = cardinality(children_names));
