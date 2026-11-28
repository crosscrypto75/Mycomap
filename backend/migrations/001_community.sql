-- Initial community schema. Apply only to a development Supabase project first.
begin;
create table public.community_profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 display_name text not null check (char_length(display_name) between 2 and 60),
 created_at timestamptz not null default now()
);
create table public.community_roles (
 user_id uuid references public.community_profiles(id) on delete cascade,
 role text check (role in ('founder','expert','association','moderator','admin')),
 primary key(user_id,role)
);
create function public.community_has_role(wanted text) returns boolean language sql stable security definer set search_path = '' as $$
 select exists(select 1 from public.community_roles where user_id=auth.uid() and role=wanted);
$$;
revoke all on function public.community_has_role(text) from public;
grant execute on function public.community_has_role(text) to authenticated;
create table public.community_rooms (
 id bigint generated always as identity primary key,
 slug text unique not null, title text not null,
 scope text not null check(scope in ('national','regional','departmental','topic','private')),
 required_role text check(required_role in ('founder','expert','association','moderator','admin')),
 active boolean not null default true
);
create function public.community_can_read_room(room bigint) returns boolean language sql stable security definer set search_path = '' as $$
 select exists(select 1 from public.community_rooms r where r.id=room and r.active and (r.required_role is null or public.community_has_role(r.required_role)));
$$;
revoke all on function public.community_can_read_room(bigint) from public;
grant execute on function public.community_can_read_room(bigint) to authenticated;
create table public.community_threads (
 id bigint generated always as identity primary key,
 room_id bigint not null references public.community_rooms(id),
 author_id uuid not null references public.community_profiles(id) on delete cascade,
 title text not null check(char_length(title) between 3 and 160),
 kind text not null default 'discussion' check(kind in ('discussion','identification','knowledge','event','suggestion')),
 body text not null check(char_length(body) between 1 and 10000),
 created_at timestamptz not null default now(),
 hidden boolean not null default false
);
create table public.community_messages (
 id bigint generated always as identity primary key,
 thread_id bigint not null references public.community_threads(id) on delete cascade,
 author_id uuid not null references public.community_profiles(id) on delete cascade,
 body text not null check(char_length(body) between 1 and 5000),
 created_at timestamptz not null default now(),
 hidden boolean not null default false
);
create table public.community_reports (
 id bigint generated always as identity primary key,
 reporter_id uuid not null references public.community_profiles(id) on delete cascade,
 thread_id bigint references public.community_threads(id) on delete cascade,
 message_id bigint references public.community_messages(id) on delete cascade,
 reason text not null check(char_length(reason) between 3 and 1000),
 created_at timestamptz not null default now(),
 check(num_nonnulls(thread_id,message_id)=1)
);
create table public.community_expert_applications (
 user_id uuid primary key references public.community_profiles(id) on delete cascade,
 experience text not null check(char_length(experience) between 10 and 4000),
 affiliation text check(char_length(affiliation)<=300),
 created_at timestamptz not null default now()
);
create index community_threads_room_time on public.community_threads(room_id,created_at desc);
create index community_messages_thread_time on public.community_messages(thread_id,created_at,id);
create index community_threads_search on public.community_threads using gin(to_tsvector('french',title||' '||body));
alter table public.community_profiles enable row level security;
alter table public.community_roles enable row level security;
alter table public.community_rooms enable row level security;
alter table public.community_threads enable row level security;
alter table public.community_messages enable row level security;
alter table public.community_reports enable row level security;
alter table public.community_expert_applications enable row level security;
revoke all on public.community_profiles,public.community_roles,public.community_rooms,public.community_threads,public.community_messages,public.community_reports,public.community_expert_applications from anon,authenticated;
grant select on public.community_profiles,public.community_rooms,public.community_threads,public.community_messages to authenticated;
grant select on public.community_roles,public.community_reports,public.community_expert_applications to authenticated;
grant insert(id,display_name) on public.community_profiles to authenticated;
grant update(display_name) on public.community_profiles to authenticated;
grant insert(room_id,author_id,title,kind,body) on public.community_threads to authenticated;
grant insert(thread_id,author_id,body) on public.community_messages to authenticated;
grant insert(reporter_id,thread_id,message_id,reason) on public.community_reports to authenticated;
grant insert(user_id,experience,affiliation) on public.community_expert_applications to authenticated;
create policy profile_read on public.community_profiles for select to authenticated using(true);
create policy profile_create on public.community_profiles for insert to authenticated with check(id=auth.uid());
create policy profile_update on public.community_profiles for update to authenticated using(id=auth.uid()) with check(id=auth.uid());
create policy roles_read on public.community_roles for select to authenticated using(user_id=auth.uid());
create policy room_read on public.community_rooms for select to authenticated using(public.community_can_read_room(id));
create policy thread_read on public.community_threads for select to authenticated using(not hidden and public.community_can_read_room(room_id));
create policy thread_create on public.community_threads for insert to authenticated with check(author_id=auth.uid() and not hidden and public.community_can_read_room(room_id));
create policy message_read on public.community_messages for select to authenticated using(not hidden and exists(select 1 from public.community_threads t where t.id=thread_id));
create policy message_create on public.community_messages for insert to authenticated with check(author_id=auth.uid() and not hidden and exists(select 1 from public.community_threads t where t.id=thread_id));
create policy report_read on public.community_reports for select to authenticated using(reporter_id=auth.uid() or public.community_has_role('moderator') or public.community_has_role('admin'));
create policy report_create on public.community_reports for insert to authenticated with check(reporter_id=auth.uid() and (exists(select 1 from public.community_threads t where t.id=thread_id) or exists(select 1 from public.community_messages m where m.id=message_id)));
create policy application_read on public.community_expert_applications for select to authenticated using(user_id=auth.uid() or public.community_has_role('admin'));
create policy application_create on public.community_expert_applications for insert to authenticated with check(user_id=auth.uid());
insert into public.community_rooms(slug,title,scope,required_role) values
 ('france','France','national',null),('pays-de-la-loire','Pays de la Loire','regional',null),
 ('identification','Identification collaborative','topic',null),('terrain','Techniques de prospection','topic',null),
 ('connaissances','Connaissances mycologiques','topic',null),('sorties','Stages et sorties','topic',null),
 ('fondateurs','Membres fondateurs','private','founder'),('experts','Mycologues','private','expert');
commit;
