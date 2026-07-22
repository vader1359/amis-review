import { randomUUID } from 'node:crypto';
import { createClient } from '@supabase/supabase-js';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

function jsonError(message, status) {
  return Response.json({ error: message }, { status });
}

export async function POST(request) {
  const supabaseUrl = process.env.SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceRoleKey) {
    return jsonError('Supabase server configuration is incomplete', 503);
  }

  const authorization = request.headers.get('authorization') || '';
  const accessToken = authorization.startsWith('Bearer ') ? authorization.slice(7).trim() : '';
  if (!accessToken) {
    return jsonError('authenticated bearer is required', 401);
  }

  let payload;
  try {
    payload = await request.json();
  } catch {
    return jsonError('upload metadata is invalid', 400);
  }

  const teamId = typeof payload.team_id === 'string' ? payload.team_id : '';
  const filename = typeof payload.filename === 'string' ? payload.filename : '';
  const contentType = typeof payload.content_type === 'string' ? payload.content_type : '';
  const byteSize = Number(payload.byte_size);
  const safeFilename = filename && filename === filename.split(/[\\/]/).pop();
  if (
    !/^[0-9a-f-]{36}$/i.test(teamId) ||
    !safeFilename ||
    !filename.toLowerCase().endsWith('.xlsx') ||
    contentType !== XLSX_TYPE ||
    !Number.isInteger(byteSize) ||
    byteSize < 1 ||
    byteSize > MAX_UPLOAD_BYTES
  ) {
    return jsonError('file must be a safe XLSX up to 25 MB', 400);
  }

  const admin = createClient(supabaseUrl, serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
  const { data: userData, error: userError } = await admin.auth.getUser(accessToken);
  if (userError || !userData.user) {
    return jsonError('authenticated user is unavailable', 401);
  }

  const { data: membership, error: membershipError } = await admin
    .from('team_memberships')
    .select('team_id')
    .eq('profile_id', userData.user.id)
    .eq('team_id', teamId)
    .maybeSingle();
  if (membershipError) {
    return jsonError('team membership lookup failed', 502);
  }
  if (!membership) {
    return jsonError('team membership is required', 403);
  }

  const stagingPath = `${teamId}/staging/${randomUUID()}.xlsx`;
  const { data, error } = await admin.storage
    .from('psi-source')
    .createSignedUploadUrl(stagingPath);
  if (error || !data?.token) {
    return jsonError('could not prepare source upload', 502);
  }

  return Response.json({ staging_path: stagingPath, upload_token: data.token });
}
