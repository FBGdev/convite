-- O convite não emite mais códigos de edição.
-- Preserva os hashes antigos e permite novas respostas sem esse campo.
alter table public.rsvps
  alter column edit_code_hash drop not null;
