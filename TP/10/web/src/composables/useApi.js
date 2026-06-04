// Definir base URL para el proxy del API
const API_BASE = '/api'

// Realizar llamada fetch al API y devolver JSON con status
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  const res = await fetch(url, { headers, ...options })
  const data = await res.json()
  return { status: res.status, data }
}

// Exponer metodos del API para cada endpoint
export function useApi() {
  return {
    getContractAddress: () => apiFetch('/contract-address'),
    getAdminAddress: () => apiFetch('/admin/address'),
    getAdminNonce: () => apiFetch('/admin/nonce'),
    getRegistration: (address) => apiFetch(`/registrations/${address}`),
    getCreators: () => apiFetch('/creators'),
    getPendingCreators: () => apiFetch('/admin/pending'),
    postRegister: (address, signature, name) =>
      apiFetch('/register', { method: 'POST', body: JSON.stringify({ address, signature, name }) }),
    patchRegistration: (address, signature, name) =>
      apiFetch(`/registrations/${address}`, { method: 'PATCH', body: JSON.stringify({ signature, name }) }),
    postAuthorize: (address, signature) =>
      apiFetch(`/authorize/${address}`, { method: 'POST', body: JSON.stringify({ signature }) }),
    postUnauthorize: (address, signature) =>
      apiFetch(`/unauthorize/${address}`, { method: 'POST', body: JSON.stringify({ signature }) }),
  }
}
