-- Add optional title and tags to quick notes and ensure timestamps keep updating.
alter table public.quick_notes
    add column if not exists title text,
    add column if not exists tags text[] default '{}'::text[];

-- Ensure the default applies when column already existed without default.
alter table public.quick_notes
    alter column tags set default '{}'::text[];

-- Trigger to maintain updated_at on every write.
create or replace function public.set_quick_notes_updated_at()
returns trigger as $$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$$ language plpgsql;

create trigger set_quick_notes_updated_at
before update on public.quick_notes
for each row
execute function public.set_quick_notes_updated_at();
