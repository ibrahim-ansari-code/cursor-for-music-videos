drop schema if exists "dev";


revoke delete on table "public"."wrappers_fdw_stats" from "anon";

revoke insert on table "public"."wrappers_fdw_stats" from "anon";

revoke references on table "public"."wrappers_fdw_stats" from "anon";

revoke select on table "public"."wrappers_fdw_stats" from "anon";

revoke trigger on table "public"."wrappers_fdw_stats" from "anon";

revoke truncate on table "public"."wrappers_fdw_stats" from "anon";

revoke update on table "public"."wrappers_fdw_stats" from "anon";

revoke delete on table "public"."wrappers_fdw_stats" from "authenticated";

revoke insert on table "public"."wrappers_fdw_stats" from "authenticated";

revoke references on table "public"."wrappers_fdw_stats" from "authenticated";

revoke select on table "public"."wrappers_fdw_stats" from "authenticated";

revoke trigger on table "public"."wrappers_fdw_stats" from "authenticated";

revoke truncate on table "public"."wrappers_fdw_stats" from "authenticated";

revoke update on table "public"."wrappers_fdw_stats" from "authenticated";

revoke delete on table "public"."wrappers_fdw_stats" from "postgres";

revoke insert on table "public"."wrappers_fdw_stats" from "postgres";

revoke references on table "public"."wrappers_fdw_stats" from "postgres";

revoke select on table "public"."wrappers_fdw_stats" from "postgres";

revoke trigger on table "public"."wrappers_fdw_stats" from "postgres";

revoke truncate on table "public"."wrappers_fdw_stats" from "postgres";

revoke update on table "public"."wrappers_fdw_stats" from "postgres";

revoke delete on table "public"."wrappers_fdw_stats" from "service_role";

revoke insert on table "public"."wrappers_fdw_stats" from "service_role";

revoke references on table "public"."wrappers_fdw_stats" from "service_role";

revoke select on table "public"."wrappers_fdw_stats" from "service_role";

revoke trigger on table "public"."wrappers_fdw_stats" from "service_role";

revoke truncate on table "public"."wrappers_fdw_stats" from "service_role";

revoke update on table "public"."wrappers_fdw_stats" from "service_role";

drop extension if exists "wrappers";
