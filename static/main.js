const cards = document.querySelectorAll('.card');
const tokenInput = document.getElementById('token');      // puede no existir
const tokenStatus = document.getElementById('tokenStatus'); // puede no existir

function getToken() {
  return tokenInput ? tokenInput.value.trim() : "";
}

function withToken(url) {
  const t = getToken();
  if (!t) return url;               // sin token => URL limpia
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}token=${encodeURIComponent(t)}`;
}

async function fetchState() {
  try {
    const res = await fetch(withToken(`/api/relays`));
    if (!res.ok) throw new Error('Error estado');
    const data = await res.json();

    if (tokenStatus) {
      tokenStatus.textContent = getToken() ? 'Token OK' : 'Sin token';
      tokenStatus.className = getToken() ? 'token-ok' : 'token-bad';
    }

    for (const card of cards) {
      const pin = parseInt(card.dataset.pin, 10);
      const label = card.querySelector('.label');
      const on = !!data.state[pin];
      label.textContent = on ? 'ON' : 'OFF';
      card.classList.toggle('on', on);
      card.classList.toggle('off', !on);
    }
  } catch (e) {
    if (tokenStatus) {
      tokenStatus.textContent = 'Error de conexión';
      tokenStatus.className = 'token-bad';
    }
    console.error(e);
  }
}

async function act(pin, action) {
  const res = await fetch(withToken(`/api/relay/${pin}/${action}`), { method: 'POST' });
  if (!res.ok) {
    const txt = await res.text();
    alert(`Error: ${txt}`);
    return;
  }
  await fetchState();
}

for (const card of cards) {
  const pin = parseInt(card.dataset.pin, 10);
  card.querySelector('.btn-on').addEventListener('click', () => act(pin, 'on'));
  card.querySelector('.btn-off').addEventListener('click', () => act(pin, 'off'));
  card.querySelector('.btn-toggle').addEventListener('click', () => act(pin, 'toggle'));
}

if (tokenInput) tokenInput.addEventListener('input', fetchState);

// Carga inicial
fetchState();
