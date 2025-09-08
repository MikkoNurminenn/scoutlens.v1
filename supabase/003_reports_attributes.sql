alter table public.reports
add column if not exists attributes jsonb not null default '{}'::jsonb;

create index if not exists idx_reports_attributes_gin
  on public.reports using gin (attributes);
