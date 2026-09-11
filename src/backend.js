(() => {
  'use strict';

  const SUPABASE_URL = 'https://bzqtgcopnnscvacynybl.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_C34DQ7afa0EjU6eJstFWJw_RizL3YzU';
  const SESSION_KEY = 'acadeloop_supabase_session_v1';
  const TEST_HOSTS = new Set(['', 'localhost', '127.0.0.1']);
  const testMode = location.protocol === 'file:' || location.protocol === 'about:' || TEST_HOSTS.has(location.hostname) || window.__ACADELOOP_TEST_MODE__ === true;

  function captureAuthRedirectSession() {
    if (testMode || !location.hash) return;
    const hash = new URLSearchParams(location.hash.replace(/^#/, ''));
    const access_token = hash.get('access_token');
    const refresh_token = hash.get('refresh_token');
    if (!access_token || !refresh_token) return;
    const expires_in = Number(hash.get('expires_in') || 3600);
    writeSession({ access_token, refresh_token, token_type: hash.get('token_type') || 'bearer', expires_in, expires_at: Math.floor(Date.now()/1000) + expires_in });
    history.replaceState(null, document.title, location.pathname + location.search);
  }

  function jsonHeaders(token, extra={}) {
    return {
      apikey: SUPABASE_KEY,
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...extra,
    };
  }

  function readSession() {
    try { return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); } catch { return null; }
  }
  function writeSession(session) {
    try {
      if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      else localStorage.removeItem(SESSION_KEY);
    } catch {}
  }

  captureAuthRedirectSession();

  async function parseError(response) {
    let payload = null;
    try { payload = await response.json(); } catch {}
    const message = payload?.msg || payload?.message || payload?.error_description || payload?.error || `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    return error;
  }

  async function fetchJson(path, options={}) {
    const response = await fetch(`${SUPABASE_URL}${path}`, options);
    if (!response.ok) throw await parseError(response);
    if (response.status === 204) return null;
    const text = await response.text();
    return text ? JSON.parse(text) : null;
  }

  async function refreshSessionIfNeeded() {
    let session = readSession();
    if (!session?.access_token) return null;
    const expiresAt = Number(session.expires_at || 0) * 1000;
    if (expiresAt && Date.now() < expiresAt - 60_000) return session;
    if (!session.refresh_token) { writeSession(null); return null; }
    try {
      const next = await fetchJson('/auth/v1/token?grant_type=refresh_token', {
        method: 'POST', headers: jsonHeaders(), body: JSON.stringify({ refresh_token: session.refresh_token })
      });
      writeSession(next);
      return next;
    } catch {
      writeSession(null);
      return null;
    }
  }

  async function accessToken() {
    const session = await refreshSessionIfNeeded();
    return session?.access_token || '';
  }

  async function requestOtp(email) {
    return fetchJson('/auth/v1/otp', {
      method: 'POST', headers: jsonHeaders(), body: JSON.stringify({ email, create_user: false })
    });
  }

  async function verifyOtp(email, token) {
    const session = await fetchJson('/auth/v1/verify', {
      method: 'POST', headers: jsonHeaders(), body: JSON.stringify({ email, token, type: 'email' })
    });
    writeSession(session);
    return session;
  }

  async function signOut() {
    const token = await accessToken();
    if (token) {
      try { await fetchJson('/auth/v1/logout', { method: 'POST', headers: jsonHeaders(token) }); } catch {}
    }
    writeSession(null);
  }

  async function currentAuthUser() {
    const token = await accessToken();
    if (!token) return null;
    try { return await fetchJson('/auth/v1/user', { headers: jsonHeaders(token) }); }
    catch { writeSession(null); return null; }
  }

  async function db(path, options={}) {
    const token = await accessToken();
    if (!token) throw new Error('Your session has expired. Please sign in again.');
    return fetchJson(`/rest/v1/${path}`, {
      ...options,
      headers: jsonHeaders(token, options.headers || {}),
    });
  }

  const q = encodeURIComponent;
  async function select(table, query='select=*') {
    return db(`${table}?${query}`, { method: 'GET' });
  }
  async function insert(table, row, options={}) {
    return db(`${table}${options.onConflict ? `?on_conflict=${q(options.onConflict)}` : ''}`, {
      method: 'POST',
      headers: { Prefer: options.upsert ? 'resolution=merge-duplicates,return=representation' : 'return=representation' },
      body: JSON.stringify(row),
    });
  }
  async function patch(table, filter, changes) {
    return db(`${table}?${filter}`, {
      method: 'PATCH', headers: { Prefer: 'return=representation' }, body: JSON.stringify(changes)
    });
  }
  async function rpc(name, body={}) {
    return db(`rpc/${name}`, { method: 'POST', body: JSON.stringify(body) });
  }
  async function profile() {
    const user = await currentAuthUser();
    if (!user?.id) return null;
    const rows = await select('profiles', `id=eq.${q(user.id)}&select=id,email,title_prefix,first_name,last_name,department,role,active,default_program_id,limit_program_access,created_at`);
    return rows?.[0] || null;
  }
  async function invoke(name, body, responseType='json') {
    const token = await accessToken();
    if (!token) throw new Error('Your session has expired. Please sign in again.');
    const response = await fetch(`${SUPABASE_URL}/functions/v1/${name}`, {
      method: 'POST', headers: jsonHeaders(token), body: JSON.stringify(body || {})
    });
    if (!response.ok) throw await parseError(response);
    if (responseType === 'blob') return response.blob();
    return response.json();
  }

  window.AcadeloopBackend = {
    enabled: !testMode,
    url: SUPABASE_URL,
    requestOtp, verifyOtp, signOut, currentAuthUser, profile,
    select, insert, patch, rpc, invoke, accessToken,
    session: readSession,
  };
})();
