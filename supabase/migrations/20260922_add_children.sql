-- A coluna companions passa a representar acompanhantes adultos.
-- Respostas existentes permanecem com zero criancas, pois antes nao havia distincao.
alter table public.rsvps
  add column children smallint not null default 0;

alter table public.rsvps
  drop constraint rsvps_companions_check,
  add constraint rsvps_companions_check check (companions between 0 and 8),
  add constraint rsvps_children_check check (children between 0 and 8),
  add constraint rsvps_extra_guests_limit check (companions + children <= 8),
  drop constraint companions_only_when_attending,
  add constraint extras_only_when_attending check (attending or (companions = 0 and children = 0));
