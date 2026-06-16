// Definir base URL para el proxy del API
const API_BASE = '/api'
// Realizar llamada fetch al API y devolver JSON con status
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`
  const headers = { ...options.headers }
  
  // Si el cuerpo NO es FormData, forzamos application/json por defecto
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json'
  }
  const res = await fetch(url, { ...options, headers })
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
      
    getCalls: (creator) =>
      apiFetch(`/calls${creator ? `?creator=${creator}` : ''}`),
    postCreateCall: (callId, signature, title, description) =>
      apiFetch('/create', { method: 'POST', body: JSON.stringify({ callId, signature, title, description }) }),
    // --- NUEVOS ENDPOINTS PARA ETAPA 3 ---
    
    // Presentar propuesta (envía solo los hashes)
    postRegisterProposal: (callId, title, description, files) =>
      apiFetch('/register-proposal', { method: 'POST', body: JSON.stringify({ callId, title, description, files }) }),
    
    // Verificar prueba de Merkle de una propuesta
    postVerifyProof: (proposalId, leaf, proof) =>
      apiFetch('/verify-proof', { method: 'POST', body: JSON.stringify({ proposalId, leaf, proof }) }),
    
    // Entrega post-cierre (envía archivos físicos y el recibo JSON, usa FormData)
    postDeliver: (formData) =>
      apiFetch('/deliver', { method: 'POST', body: formData }),
      
    // Consultar datos de entrega y lista de archivos
    getDeliveryInfo: (proposalId) =>
      apiFetch(`/deliveries/${proposalId}`)
  }
}