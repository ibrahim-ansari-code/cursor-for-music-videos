create schema if not exists "dev";


alter table "public"."user_agent_threads" enable row level security;

create policy "User Agent Threads Delete Access Control"
on "public"."user_agent_threads"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (user_id = ( SELECT auth.uid() AS uid)))));


create policy "User Agent Threads Insert Access Control"
on "public"."user_agent_threads"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (user_id = ( SELECT auth.uid() AS uid)))));


create policy "User Agent Threads Select Access Control"
on "public"."user_agent_threads"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (user_id = ( SELECT auth.uid() AS uid)))));


create policy "User Agent Threads Update Access Control"
on "public"."user_agent_threads"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (user_id = ( SELECT auth.uid() AS uid)))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (user_id = ( SELECT auth.uid() AS uid)))));



