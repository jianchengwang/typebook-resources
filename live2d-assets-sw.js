/* Private Live2D bridge: no token in URLs, cache or persistent storage. */
const sessions = new Map();
const PREFIX = '/__typebook_live2d/';
// One budget includes response headers, body transfer and at most one safe retry.
const RESOURCE_TIMEOUT_MS = 90000;
const RETRYABLE_STATUS = new Set([502, 503, 504]);
function releaseSession(session) {
  if (!session) return;
  session.released = true;
  for (const controller of session.requests) controller.abort();
  session.requests.clear();
}
const api = new URL(new URL(self.location.href).searchParams.get('api') || self.location.origin);
const trustedApi = !api.username && !api.password && !api.search && !api.hash &&
  (api.protocol === 'https:' || (api.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(api.hostname)));
self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('message', event => {
  const data = event.data || {}, client = event.source?.id;
  const reply = value => event.ports[0]?.postMessage(value);
  if (!trustedApi || !client || !/^[a-f0-9]{32}$/.test(data.nonce || '')) return reply({error: 'Invalid asset session'});
  const key = client + ':' + data.nonce;
  if (data.action === 'release') { releaseSession(sessions.get(key)); sessions.delete(key); return reply({ok: true}); }
  if (data.action === 'refresh') {
    const session = sessions.get(key);
    if (!session) return reply({error: 'Asset session expired'});
    session.token = typeof data.token === 'string' ? data.token : '';
    session.expires = Date.now() + 15 * 60 * 1000;
    return reply({ok: true});
  }
  try {
    const root = new URL(data.root);
    if (root.origin !== api.origin || !root.pathname.startsWith(api.pathname.replace(/\/$/, '') + '/objects/live2d/') ||
        root.username || root.password || root.search || root.hash || !root.pathname.endsWith('/')) throw Error();
    for (const [id, session] of sessions) if (session.expires < Date.now()) { releaseSession(session); sessions.delete(id); }
    if ([...sessions.keys()].filter(id => id.startsWith(client + ':')).length >= 4) throw Error();
    releaseSession(sessions.get(key));
    sessions.set(key, {root: root.href, token: typeof data.token === 'string' ? data.token : '', expires: Date.now() + 15 * 60 * 1000, requests: new Set(), released: false});
    reply({ok: true});
  } catch { reply({error: 'Only configured Worker Live2D objects are allowed'}); }
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(PREFIX)) return;
  event.respondWith((async () => {
    const fail = () => new Response('Asset session unavailable', {status: 403, headers: {'Cache-Control': 'no-store'}});
    const rest = url.pathname.slice(PREFIX.length), split = rest.indexOf('/');
    if (split < 0 || url.search || !['GET', 'HEAD'].includes(event.request.method)) return fail();
    const nonce = rest.slice(0, split);
    const session = sessions.get(event.clientId + ':' + nonce);
    if (!session || session.expires < Date.now()) return fail();
    const target = new URL(rest.slice(split + 1), session.root);
    if (!target.href.startsWith(session.root) || target.search || target.hash) return fail();
    const headers = new Headers();
    if (session.token) headers.set('Authorization', 'Bearer ' + session.token);
    if (event.request.headers.has('Range')) headers.set('Range', event.request.headers.get('Range'));
    const controller = new AbortController();
    session.requests.add(controller);
    let timedOut = false, notified = false, reader;
    const notify = async (status, kind) => {
      if (notified || session.released || event.request.signal.aborted) return;
      notified = true;
      const client = await self.clients.get(event.clientId);
      client?.postMessage({type: 'typebook-character-asset-error', nonce, resource: target.pathname.split('/').pop(), status, kind});
    };
    const timer = setTimeout(() => { timedOut = true; controller.abort(); void reader?.cancel().catch(() => {}); void notify(504, 'timeout'); }, RESOURCE_TIMEOUT_MS);
    const requestAborted = () => controller.abort();
    event.request.signal.addEventListener('abort', requestAborted, {once: true});
    if (event.request.signal.aborted) controller.abort();
    const cleanup = () => { clearTimeout(timer); session.requests.delete(controller); event.request.signal.removeEventListener('abort', requestAborted); };
    controller.signal.addEventListener('abort', () => { cleanup(); void reader?.cancel().catch(() => {}); }, {once: true});
    const pause = () => new Promise((resolve, reject) => {
      const aborted = () => { clearTimeout(delay); controller.signal.removeEventListener('abort', aborted); reject(new Error('Asset request cancelled')); };
      const delay = setTimeout(() => { controller.signal.removeEventListener('abort', aborted); resolve(); }, 400);
      controller.signal.addEventListener('abort', aborted, {once: true});
      if (controller.signal.aborted) aborted();
    });
    try {
      let upstream;
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          upstream = await fetch(target.href, {method: event.request.method, headers, cache: 'no-store', credentials: 'omit', redirect: 'error', signal: controller.signal});
        } catch (error) {
          if (attempt || controller.signal.aborted) throw error;
          await pause(); continue;
        }
        let temporary = RETRYABLE_STATUS.has(upstream.status);
        // Integrity/registration metadata failures are permanent, even though the API uses 503.
        if (upstream.status === 503 && upstream.headers.get('content-type')?.includes('json')) {
          const failure = await upstream.clone().json().catch(() => null);
          if (JSON.stringify(failure).includes('CHARACTER_')) temporary = false;
        }
        if (attempt === 0 && temporary) { await upstream.body?.cancel(); await pause(); continue; }
        break;
      }
      if (controller.signal.aborted) throw new Error('Asset request cancelled');
      if (!upstream.ok) {
        await notify(upstream.status, 'http');
        await upstream.body?.cancel(); cleanup();
        return new Response('Character asset request failed', {status: upstream.status, headers: {'Cache-Control': 'no-store'}});
      }
      if (target.pathname.endsWith('.json') && event.request.method !== 'HEAD') {
        try { await upstream.clone().json(); }
        catch (error) {
          if (controller.signal.aborted) throw error;
          await notify(422, 'format'); await upstream.body?.cancel(); cleanup();
          return new Response('Character JSON is invalid', {status: 422, headers: {'Cache-Control': 'no-store'}});
        }
      }
      const output = new Headers(upstream.headers);
      output.set('Cache-Control', 'no-store');
      output.set('X-Content-Type-Options', 'nosniff');
      if (!upstream.body) { cleanup(); return new Response(null, {status: upstream.status, headers: output}); }
      reader = upstream.body.getReader();
      const body = new ReadableStream({
        async pull(stream) {
          try {
            const chunk = await reader.read();
            if (controller.signal.aborted) throw new Error('Asset request cancelled');
            if (chunk.done) { cleanup(); stream.close(); } else stream.enqueue(chunk.value);
          } catch (error) { cleanup(); await notify(timedOut ? 504 : 502, timedOut ? 'timeout' : 'network'); stream.error(error); }
        },
        cancel() { controller.abort(); cleanup(); return reader.cancel(); }
      });
      return new Response(body, {status: upstream.status, headers: output});
    } catch {
      cleanup();
      // An aborted renderer must receive a rejected fetch, not an HTTP body which
      // this SDK would parse as an empty moc and continue after disposal.
      if (session.released || event.request.signal.aborted) return Response.error();
      await notify(timedOut ? 504 : 502, timedOut ? 'timeout' : 'network');
      return new Response('Character asset could not load', {status: timedOut ? 504 : 502, headers: {'Cache-Control': 'no-store'}});
    }
  })());
});
