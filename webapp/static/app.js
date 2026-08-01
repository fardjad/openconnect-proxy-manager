async function api(path, method='GET', body=null) {
  const opts = {method, headers:{'Content-Type':'application/json'}};
  if (body) opts.body = JSON.stringify(body);
  return fetch(path, opts).then(r => r.json());
}

async function refresh() {
  const s = await api('/api/status');
  document.getElementById('status-text').textContent = s.state.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
  document.getElementById('status-msg').textContent = s.msg||'';
  document.querySelector('.dot').style.setProperty('--status-color', s.color);
  document.getElementById('btn-connect').disabled = s.state !== 'disconnected' && s.state !== 'error';
  document.getElementById('btn-disconnect').disabled = s.state === 'disconnected';
  document.getElementById('mfa-section').style.display = s.state === 'waiting_mfa' ? 'block' : 'none';
  document.getElementById('logs').innerHTML = (s.output||[]).join('<br>') || '\u2014';
}

async function connect() {
  const body = {};
  const u = document.getElementById('vpn-user');
  const p = document.getElementById('vpn-pass');
  if (u) body.user = u.value;
  if (p) body.password = p.value;
  await api('/api/connect','POST',body);
  refresh();
}

async function disconnect() { await api('/api/disconnect','POST'); refresh(); }

async function submitMfa() {
  const code = document.getElementById('mfa-code').value;
  if (!code) return;
  await api('/api/mfa','POST',{code});
  document.getElementById('mfa-code').value = '';
  refresh();
}

setInterval(refresh, 2000);
refresh();