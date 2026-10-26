-- Migration `add_delete_user_account_function`. Kept here as a record: this repo
-- does not otherwise version the schema, which lives in Supabase.
--
-- Self-service account deletion, called only by the backend (service_role) from
-- POST /auth/delete-account. One transaction: if any step fails nothing is deleted,
-- so a person is never left half-deleted (profile gone but login identity kept, or
-- vice versa).
create or replace function public.delete_user_account(p_user_id uuid)
returns void
language plpgsql
security definer
set search_path = public, auth, pg_temp
as $$
declare
  v_auth_user_id uuid;
begin
  -- Deleting the profile row cascades to everything that holds this person's
  -- data: enrollments, chat_sessions (-> chat_messages), quiz_attempts,
  -- mastery_scores, mind_maps, study_plans, calendar_cache, student_materials,
  -- sessions, notifications, parent_links. audit_logs, api_usage,
  -- shared_materials.uploaded_by and platform_config.updated_by reference the
  -- user with ON DELETE SET NULL: the row stays, the link to the person goes.
  delete from public.users where id = p_user_id returning auth_user_id into v_auth_user_id;
  if not found then
    raise exception 'user % not found', p_user_id using errcode = 'P0002';
  end if;

  -- The Supabase Auth identity (email, password hash, auth sessions) is not
  -- covered by that cascade (users.auth_user_id is ON DELETE SET NULL), so it
  -- is removed explicitly. auth.identities / auth.sessions / refresh tokens
  -- cascade from auth.users.
  if v_auth_user_id is not null then
    delete from auth.users where id = v_auth_user_id;
  end if;
end;
$$;

-- Postgres grants EXECUTE to PUBLIC on new functions by default. The anon key is
-- public (the keep-alive workflow embeds it), so lock this down explicitly.
revoke all on function public.delete_user_account(uuid) from public, anon, authenticated;
grant execute on function public.delete_user_account(uuid) to service_role;
