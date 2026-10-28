(() => {
  'use strict';

  const SUPABASE_URL = 'https://bzqtgcopnnscvacynybl.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_C34DQ7afa0EjU6eJstFWJw_RizL3YzU';
  const SESSION_KEY = 'acadeloop_supabase_session_v2';
  const LEGACY_SESSION_KEYS = ['acadeloop_supabase_session_v1'];
  const SESSION_MAX_AGE_MS = 12 * 60 * 60 * 1000;
  const TEST_HOSTS = new Set(['localhost', '127.0.0.1']);
  // TEMPORARY: set false and rebuild to remove hosted role login and restore OTP.
  const TEMPORARY_ROLE_LOGIN = true;
  const localTestMode = location.protocol === 'file:' || location.protocol === 'about:' || TEST_HOSTS.has(location.hostname) || window.__ACADELOOP_TEST_MODE__ === true;
  const testMode = TEMPORARY_ROLE_LOGIN || localTestMode;
  const normalizeEmail = value => String(value || '').trim().toLowerCase();
  const validEmail = value => {
    const email = normalizeEmail(value);
    return email.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/u.test(email);
  };

  // v1 stored refresh credentials in localStorage. Never restore them after this
  // security upgrade: a login is now limited to the current browser tab/session.
  for (const key of LEGACY_SESSION_KEYS) {
    try { localStorage.removeItem(key); } catch {}
  }

  function readSession() {
    try {
      const session = JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null');
      if (!session) return null;
      const startedAt = Number(session.client_started_at || 0);
      if (!startedAt || Date.now() - startedAt > SESSION_MAX_AGE_MS) {
        sessionStorage.removeItem(SESSION_KEY);
        return null;
      }
      return session;
    } catch { return null; }
  }

  function writeSession(session, preserveStartedAt=true) {
    try {
      if (!session) {
        sessionStorage.removeItem(SESSION_KEY);
        return;
      }
      const prior = preserveStartedAt ? readSession() : null;
      const client_started_at = Number(prior?.client_started_at || session.client_started_at || Date.now());
      sessionStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, client_started_at }));
    } catch {}
  }

  function discardSession() { writeSession(null); }

  function captureAuthRedirectSession() {
    if (testMode || !location.hash) return;
    const hash = new URLSearchParams(location.hash.replace(/^#/, ''));
    const access_token = hash.get('access_token');
    const refresh_token = hash.get('refresh_token');
    if (!access_token || !refresh_token) return;
    const expires_in = Number(hash.get('expires_in') || 3600);
    writeSession({ access_token, refresh_token, token_type: hash.get('token_type') || 'bearer', expires_in, expires_at: Math.floor(Date.now()/1000) + expires_in, client_started_at: Date.now() }, false);
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
    if (testMode) throw new Error('Test workspaces use browser sample data only.');
    const response = await fetch(`${SUPABASE_URL}${path}`, { ...options, cache: 'no-store' });
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
    if (!session.refresh_token) { discardSession(); return null; }
    try {
      const next = await fetchJson('/auth/v1/token?grant_type=refresh_token', {
        method: 'POST', headers: jsonHeaders(), body: JSON.stringify({ refresh_token: session.refresh_token })
      });
      writeSession({ ...next, client_started_at: session.client_started_at });
      return readSession();
    } catch {
      discardSession();
      return null;
    }
  }

  async function accessToken() {
    if (testMode) return '';
    const session = await refreshSessionIfNeeded();
    return session?.access_token || '';
  }

  async function requestOtp(emailValue) {
    const email = normalizeEmail(emailValue);
    if (!validEmail(email)) throw new Error('Enter a complete valid email address.');
    // Starting a new sign-in must never inherit the identity of an older session.
    discardSession();
    return fetchJson('/auth/v1/otp', {
      method: 'POST', headers: jsonHeaders(), body: JSON.stringify({ email, create_user: false })
    });
  }

  async function verifyOtp(emailValue, tokenValue) {
    const email = normalizeEmail(emailValue);
    const token = String(tokenValue || '').trim();
    if (!validEmail(email)) throw new Error('Enter a complete valid email address.');
    if (!/^\d{6}$/.test(token)) throw new Error('Enter the six-digit sign-in code.');
    discardSession();
    const session = await fetchJson('/auth/v1/verify', {
      method: 'POST', headers: jsonHeaders(), body: JSON.stringify({ email, token, type: 'email' })
    });
    const sessionEmail = normalizeEmail(session?.user?.email);
    if (!session?.access_token || !session?.refresh_token || !session?.user?.id || sessionEmail !== email) {
      discardSession();
      throw new Error('The verified account did not match the requested email.');
    }
    writeSession({ ...session, client_started_at: Date.now() }, false);
    return session;
  }

  async function signOut() {
    const token = await accessToken();
    if (token) {
      try { await fetchJson('/auth/v1/logout', { method: 'POST', headers: jsonHeaders(token) }); } catch {}
    }
    discardSession();
  }

  async function currentAuthUser() {
    const token = await accessToken();
    if (!token) return null;
    try {
      const user = await fetchJson('/auth/v1/user', { headers: jsonHeaders(token) });
      if (!user?.id || !validEmail(user?.email)) throw new Error('Invalid authenticated user.');
      return user;
    } catch {
      discardSession();
      return null;
    }
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
  async function select(table, query='select=*') { return db(`${table}?${query}`, { method: 'GET' }); }
  async function insert(table, row, options={}) {
    return db(`${table}${options.onConflict ? `?on_conflict=${q(options.onConflict)}` : ''}`, {
      method: 'POST', headers: { Prefer: options.upsert ? 'resolution=merge-duplicates,return=representation' : 'return=representation' }, body: JSON.stringify(row),
    });
  }
  async function patch(table, filter, changes) {
    return db(`${table}?${filter}`, { method: 'PATCH', headers: { Prefer: 'return=representation' }, body: JSON.stringify(changes) });
  }
  async function rpc(name, body={}) { return db(`rpc/${name}`, { method: 'POST', body: JSON.stringify(body) }); }

  async function profile() {
    const user = await currentAuthUser();
    if (!user?.id) return null;
    const rows = await select('profiles', `id=eq.${q(user.id)}&select=id,email,title_prefix,first_name,last_name,department,role,active,default_program_id,limit_program_access,created_at`);
    const profile = rows?.[0] || null;
    if (!profile || normalizeEmail(profile.email) !== normalizeEmail(user.email)) {
      discardSession();
      return null;
    }
    return profile;
  }

  async function invoke(name, body, responseType='json') {
    const token = await accessToken();
    if (!token) throw new Error('Your session has expired. Please sign in again.');
    const response = await fetch(`${SUPABASE_URL}/functions/v1/${name}`, {
      method: 'POST', headers: jsonHeaders(token), body: JSON.stringify(body || {}), cache: 'no-store'
    });
    if (!response.ok) throw await parseError(response);
    if (responseType === 'blob') return response.blob();
    return response.json();
  }

  window.AcadeloopBackend = {
    enabled: !testMode,
    testMode,
    localTestMode,
    temporaryRoleLogin: TEMPORARY_ROLE_LOGIN,
    url: SUPABASE_URL,
    requestOtp, verifyOtp, signOut, discardSession, currentAuthUser, profile,
    select, insert, patch, rpc, invoke, accessToken,
    session: readSession,
  };
})();

