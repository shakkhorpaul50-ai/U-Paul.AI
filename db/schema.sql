-- Neon Free (0.5GB). State only, no vectors blobs, no pixels.
create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  role text not null default 'public' check (role in ('public','creator','debi','friend')),
  extreme_unlocked boolean not null default false,
  active_days integer not null default 0,
  dob_verified boolean not null default false,
  nsfw_consent boolean not null default false,
  nsfw_consent_ts timestamptz,
  created_at timestamptz not null default now()
);
create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  mode text not null default 'sfw' check (mode in ('sfw','nsfw')),
  skill text not null default 'general',
  created_at timestamptz not null default now()
);
create table if not exists messages (
  id bigserial primary key,
  session_id uuid references sessions(id) on delete cascade,
  role text not null check (role in ('user','assistant','system')),
  content text not null,
  tokens integer not null default 0,
  ms integer not null default 0,
  flagged boolean not null default false,
  created_at timestamptz not null default now()
);
create table if not exists routes (
  prompt_hash text primary key,
  skill text not null,
  confidence real not null default 0,
  created_at timestamptz not null default now()
);
create table if not exists feedback (
  message_id bigint references messages(id) on delete cascade,
  score smallint not null check (score between -1 and 1),
  created_at timestamptz not null default now()
);
create index if not exists idx_messages_session on messages(session_id, id);
create index if not exists idx_sessions_user on sessions(user_id);
