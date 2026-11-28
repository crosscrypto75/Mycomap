begin;
-- Badge identities are independent of future artwork and never confer permissions.
create table public.community_badges (
 code text primary key, title text not null, category text not null check(category in ('status','reward')),
 artwork_path text, enabled boolean not null default true
);
insert into public.community_badges(code,title,category) values
 ('founder','Membre fondateur','status'),('expert','Mycologue vérifié','status'),
 ('first_contribution','Première pousse','reward'),('explorer','Explorateur','reward'),
 ('photo_quality','Œil de lynx','reward'),('helpful','Entraide','reward'),
 ('knowledge','Transmission','reward'),('validated_observer','Observateur aguerri','reward'),
 ('habitat','Connaisseur des biotopes','reward'),('community_pillar','Pilier de la communauté','reward'),
 ('ai_contributor','Contributeur IA','reward'),('safety','Sentinelle','reward');
create table public.community_rewards (
 user_id uuid references public.community_profiles(id) on delete cascade,
 badge_code text references public.community_badges(code),
 awarded_at timestamptz not null default now(), evidence text not null,
 primary key(user_id,badge_code)
);
create table public.community_founder_purchases (
 provider text not null, payment_id text not null,
 user_id uuid not null unique references public.community_profiles(id) on delete restrict,
 amount_cents integer not null check(amount_cents=4999),
 currency text not null check(currency='EUR'),
 paid_at timestamptz not null default now(), revoked_at timestamptz,
 primary key(provider,payment_id)
);
-- Only a trusted backend may call this AFTER verifying a settled payment with the provider.
create function public.community_grant_founder(p_user uuid,p_provider text,p_payment text,p_amount integer,p_currency text)
returns void language plpgsql security definer set search_path='' as $$
begin
 if p_amount is distinct from 4999 or p_currency is distinct from 'EUR' or nullif(trim(p_provider),'') is null or nullif(trim(p_payment),'') is null then raise exception 'Invalid founder payment'; end if;
 insert into public.community_founder_purchases(provider,payment_id,user_id,amount_cents,currency)
 values(p_provider,p_payment,p_user,p_amount,p_currency) on conflict(provider,payment_id) do nothing;
 if not exists(select 1 from public.community_founder_purchases where provider=p_provider and payment_id=p_payment and user_id=p_user and revoked_at is null) then raise exception 'Payment already assigned or revoked'; end if;
 insert into public.community_roles(user_id,role) values(p_user,'founder') on conflict do nothing;
end; $$;
revoke all on function public.community_grant_founder(uuid,text,text,integer,text) from public,anon,authenticated;
grant execute on function public.community_grant_founder(uuid,text,text,integer,text) to service_role;
create function public.community_revoke_founder(p_provider text,p_payment text) returns void language plpgsql security definer set search_path='' as $$
declare owner_id uuid;
begin
 update public.community_founder_purchases set revoked_at=coalesce(revoked_at,now()) where provider=p_provider and payment_id=p_payment returning user_id into owner_id;
 if owner_id is not null then delete from public.community_roles where user_id=owner_id and role='founder'; end if;
end; $$;
revoke all on function public.community_revoke_founder(text,text) from public,anon,authenticated;
grant execute on function public.community_revoke_founder(text,text) to service_role;
-- Public-facing badge projection: status badges are derived from authoritative roles.
create function public.community_profile_badges(p_user uuid)
returns table(code text,title text,category text,artwork_path text)
language sql stable security definer set search_path='' as $$
 select b.code,b.title,b.category,b.artwork_path from public.community_badges b
 where b.enabled and (
 (b.category='status' and exists(select 1 from public.community_roles r where r.user_id=p_user and r.role=b.code))
 or (b.category='reward' and exists(select 1 from public.community_rewards r where r.user_id=p_user and r.badge_code=b.code)));
$$;
revoke all on function public.community_profile_badges(uuid) from public,anon;
grant execute on function public.community_profile_badges(uuid) to authenticated;
create table public.community_events (
 id bigint generated always as identity primary key,
 organizer_id uuid not null references public.community_profiles(id) on delete cascade,
 title text not null check(char_length(title) between 3 and 160),
 description text not null check(char_length(description) between 1 and 5000),
 region text not null check(char_length(region) between 2 and 100),
 starts_at timestamptz not null, capacity integer not null check(capacity between 1 and 500),
 price_cents integer not null default 0 check(price_cents>=0),
 status text not null default 'draft' check(status in ('draft','published','cancelled'))
);
alter table public.community_badges enable row level security;
alter table public.community_rewards enable row level security;
alter table public.community_founder_purchases enable row level security;
alter table public.community_events enable row level security;
revoke all on public.community_badges,public.community_rewards,public.community_founder_purchases,public.community_events from anon,authenticated;
grant select on public.community_badges,public.community_events to authenticated;
grant insert(organizer_id,title,description,region,starts_at,capacity,price_cents,status) on public.community_events to authenticated;
grant update(title,description,region,starts_at,capacity,price_cents,status) on public.community_events to authenticated;
create policy badges_read on public.community_badges for select to authenticated using(enabled);
create policy events_read on public.community_events for select to authenticated using(status='published' or organizer_id=auth.uid());
create policy events_create on public.community_events for insert to authenticated with check(organizer_id=auth.uid() and public.community_has_role('expert'));
create policy events_update on public.community_events for update to authenticated using(organizer_id=auth.uid() and public.community_has_role('expert')) with check(organizer_id=auth.uid() and public.community_has_role('expert'));
commit;
