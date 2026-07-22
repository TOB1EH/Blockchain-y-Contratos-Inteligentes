<script setup>
import { ref, watch } from 'vue'
import { Contract, keccak256, toUtf8Bytes, encodeRlp } from 'ethers'
import { useWallet } from '../composables/useWallet.js'
import { useApi } from '../composables/useApi.js'
import { buildRegisterMessage, buildUpdateMessage, buildCreateMessage } from '../utils/eip712.js'

// Declarar estado reactivo del panel de creador
const api = useApi()
const { account, signer, chainId, isConnected } = useWallet()
const status = ref(null)
const dbEntry = ref(null)
const contractAddress = ref('')
const name = ref('')
const newName = ref('')
const msg = ref('')
const loadingStatus = ref(false)
const isRegisteredOnChain = ref(false)

// Estado para el formulario de creacion de llamado
const callTitle = ref('')

const callDescription = ref('')
const now = new Date()
now.setDate(now.getDate() + 7)
const closingDateTime = ref(now.toISOString().slice(0, 16))
const creatingCall = ref(false)

// Estado para la vista de mis llamados y propuestas recibidas
const myCalls = ref([])
const loadingCalls = ref(false)
const expandedCallId = ref(null)
const callProposals = ref({})
const loadingProposals = ref({})

// Definir ABI minima del factory para registro on-chain y creacion de llamados
const FACTORY_ABI = [
  'function register()',
  'function isRegistered(address) view returns (bool)',
  'function create(bytes32 callId, uint256 timestamp)'
]

// Verificar estado del creador al conectar cuenta
watch(account, async () => {
  msg.value = ''
  if (!account.value) { 
    status.value = null; dbEntry.value = null; isRegisteredOnChain.value = false; 
    return 
  }
  loadingStatus.value = true
  const addrRes = await api.getContractAddress()
  contractAddress.value = addrRes.data.address
  
  // Consultar al contrato si ya está registrado on-chain para ocultar el Paso 1
  if (signer.value && contractAddress.value) {
    try {
      const contract = new Contract(contractAddress.value, FACTORY_ABI, signer.value)
      isRegisteredOnChain.value = await contract.isRegistered(account.value)
    } catch (e) {
      console.error("Error al consultar on-chain:", e)
    }
  }
  const regRes = await api.getRegistration(account.value)
  
  // Detectar si es admin
  const adminRes = await api.getAdminAddress()
  if (account.value.toLowerCase() === adminRes.data.address.toLowerCase()) {
    status.value = 'admin'
    loadingStatus.value = false
    return
  }
  
  // Usar el estado real de la API sin inventar el estado "none"
  if (regRes.status === 200) {
    dbEntry.value = regRes.data.name ? regRes.data : null
    status.value = regRes.data.status
  } else {
    status.value = 'pending'
    dbEntry.value = null
  }
  
  // Cargar llamados automaticamente si el creador esta autorizado
  if (status.value === 'authorized') {
    loadMyCalls()
  }
  
  loadingStatus.value = false
}, { immediate: true })

// Enviar transaccion on-chain al contrato factory
async function registerOnChain() {
  if (!signer.value || !contractAddress.value) return
  try {
    msg.value = 'Enviando transaccion on-chain...'
    const contract = new Contract(contractAddress.value, FACTORY_ABI, signer.value)
    const tx = await contract.register()
    msg.value = `Transaccion enviada: ${tx.hash}. Esperando confirmacion...`
    const receipt = await tx.wait()
    if (!receipt || receipt.status === 0) {
      throw new Error('La transaccion fallo en la cadena')
    }
    msg.value = 'Registro on-chain exitoso.'
    
    isRegisteredOnChain.value = true // Ocultar boton paso 1
    
    // Refrescar estado desde la API
    const regRes = await api.getRegistration(account.value)
    if (regRes.status === 200) {
      status.value = regRes.data.status
    }
  } catch (e) {
    msg.value = `Error: ${e.message}`
  }
}

// Firmar y enviar registro off-chain via EIP-712
async function registerOffChain() {
  if (!signer.value || !contractAddress.value || !name.value) return
  try {
    const typedData = buildRegisterMessage(chainId.value, contractAddress.value, name.value)
    const signature = await signer.value.signTypedData(
      typedData.domain, typedData.types, typedData.message
    )
    const res = await api.postRegister(account.value, signature, name.value)
    if (res.status === 200) {
      msg.value = `Registro off-chain exitoso.`
      dbEntry.value = { name: name.value, status: res.data.status, nonce: 1 }
      status.value = res.data.status
    } else {
      msg.value = `Error: ${res.data.message}`
    }
  } catch (e) {
    msg.value = `Error: ${e.message}`
  }
}

// Firmar y enviar actualizacion de perfil via EIP-712
async function updateProfile() {
  if (!signer.value || !contractAddress.value || !newName.value || !dbEntry.value) return
  try {
    const nonce = dbEntry.value.nonce || 1
    const typedData = buildUpdateMessage(chainId.value, contractAddress.value, nonce, newName.value)
    const signature = await signer.value.signTypedData(
      typedData.domain, typedData.types, typedData.message
    )
    const res = await api.patchRegistration(account.value, signature, newName.value)
    if (res.status === 200) {
      msg.value = 'Perfil actualizado'
      dbEntry.value.name = newName.value
    } else {
      msg.value = `Error: ${res.data.message}`
    }
  } catch (e) {
    msg.value = `Error: ${e.message}`
  }
}

// Calcular callId = keccak256(rlp.encode([title, description]))
function computeCallId(title, description) {
  const encoded = encodeRlp([toUtf8Bytes(title), toUtf8Bytes(description)])
  return keccak256(encoded)
}

// Crear un nuevo llamado (doble interaccion: off-chain + on-chain)
async function createCall() {
  if (!signer.value || !contractAddress.value || !callTitle.value || !callDescription.value) return
  const callId = computeCallId(callTitle.value, callDescription.value)
  creatingCall.value = true
  try {
    // Paso 1: Registrar off-chain en la API via EIP-712
    msg.value = 'Paso 1/2: Firmando mensaje off-chain...'
    const typedData = buildCreateMessage(chainId.value, contractAddress.value, callId)
    const signature = await signer.value.signTypedData(
      typedData.domain, typedData.types, typedData.message
    )
    const offRes = await api.postCreateCall(callId, signature, callTitle.value, callDescription.value)
    if (offRes.status !== 201) {
      msg.value = `Error off-chain: ${offRes.data.message}`
      creatingCall.value = false
      return
    }
    msg.value = 'Paso 1/2 completado. Ahora firma la transaccion on-chain...'

    // Paso 2: Enviar transaccion on-chain al contrato factory
    
    const closingTimestamp = Math.floor(new Date(closingDateTime.value).getTime() / 1000)

    const contract = new Contract(contractAddress.value, FACTORY_ABI, signer.value)
    const tx = await contract.create(callId, closingTimestamp)
    msg.value = `Paso 2/2: Transaccion enviada: ${tx.hash}. Esperando confirmacion...`
    const receipt = await tx.wait()
    if (!receipt || receipt.status === 0) {
      throw new Error('La transaccion de creacion fallo en la cadena')
    }
    msg.value = `Llamado creado exitosamente. La cadena lo confirmara en breve.`
    callTitle.value = ''
    callDescription.value = ''
    const nextDefault = new Date()
    nextDefault.setDate(nextDefault.getDate() + 7)
    closingDateTime.value = nextDefault.toISOString().slice(0, 16)
    // Recargar llamados para mostrar el nuevo
    await loadMyCalls()
  } catch (e) {
    msg.value = `Error: ${e.message}`
  } finally {
    creatingCall.value = false
  }
}
// Cargar los llamados creados por el creador actual
async function loadMyCalls() {
  loadingCalls.value = true
  try {
    const res = await api.getCalls(account.value)
    myCalls.value = res.data.calls || []
  } catch (e) {
    console.error('Error al cargar llamados:', e)
  } finally {
    loadingCalls.value = false
  }
}

// Cargar propuestas de un llamado
async function loadProposals(callId) {
  if (callProposals.value[callId]) return
  loadingProposals.value = { ...loadingProposals.value, [callId]: true }
  try {
    const res = await api.getCallProposals(callId)
    callProposals.value = { ...callProposals.value, [callId]: res.data.proposals || [] }
  } catch (e) {
    console.error('Error al cargar propuestas:', e)
  } finally {
    loadingProposals.value = { ...loadingProposals.value, [callId]: false }
  }
}

function toggleCall(callId) {
  if (expandedCallId.value === callId) {
    expandedCallId.value = null
  } else {
    expandedCallId.value = callId
    loadProposals(callId)
  }
}

function getProposalDownloadUrl(proposalId, fileHash) {
  return `/api/proposals/${proposalId}/files/${fileHash}`
}

</script>
<template>
  <div>
    <h2>Panel de Creador</h2>
    <div v-if="!isConnected"><p>Conecta tu wallet para ver este panel.</p></div>
    <div v-else-if="loadingStatus"><p>Cargando estado...</p></div>
    <div v-else-if="status === 'admin'">
      <p>No puedes registrarte como creador con la cuenta administradora.</p>
    </div>
    <div v-else>
      <p><strong>Direccion:</strong> {{ account }}</p>
      <p><strong>Estado:</strong> {{ status || 'pending' }}</p>
      
      <!-- Mostrar sección de registro si está en estado pending -->
      <div v-if="status === 'pending'">
        <h3>Registro</h3>
        
        <!-- Ocultar si ya está registrado en el contrato -->
        <div v-if="!isRegisteredOnChain">
          <p>Paso 1: Registrate on-chain (requiere firma MetaMask)</p>
          <button @click="registerOnChain">Registrarse on-chain</button>
          <hr>
        </div>
        
        <!-- Ocultar si ya está registrado en la base de datos de la API -->
        <div v-if="!dbEntry">
          <p>Paso 2: Registrate off-chain en la API</p>
          <input v-model="name" placeholder="Nombre" />
          <button @click="registerOffChain">Registrarse off-chain</button>
        </div>
      </div>
      
      <!-- Mostrar sección de actualizar perfil solo cuando completó ambos pasos -->
      <div v-else-if="status === 'registered' || status === 'authorized'">
        <h3>Actualizar Perfil</h3>
        <p>Nombre actual: {{ dbEntry?.name }}</p>
        <input v-model="newName" placeholder="Nuevo nombre" />
        <button @click="updateProfile">Actualizar</button>
      </div>

      <!-- Sección de creación de llamado (solo para creadores autorizados) -->
      <div v-if="status === 'authorized'">
        <hr>
        <h3>Crear Llamado</h3>
        <p>Ingresá los datos del nuevo llamado a presentación de propuestas.</p>
        <div>
          <label>Título:<br><input v-model="callTitle" placeholder="Título del llamado" :disabled="creatingCall" /></label>
        </div>
        <div>
          <label>Descripción:<br><textarea v-model="callDescription" placeholder="Descripción del llamado" :disabled="creatingCall"></textarea></label>
        </div>
        <div>
          <label>Fecha y hora de cierre:<br><input v-model="closingDateTime" type="datetime-local" :disabled="creatingCall" /></label>
        </div>
        <button @click="createCall" :disabled="creatingCall || !callTitle || !callDescription">
          {{ creatingCall ? 'Creando llamado...' : 'Crear Llamado' }}
        </button>
      </div>
      
      <!-- Sección de mis llamados y propuestas recibidas -->
      <div v-if="status === 'authorized'">
        <hr>
        <h3>Mis Llamados</h3>
        <div v-if="loadingCalls"><p>Cargando llamados...</p></div>
        <div v-else-if="myCalls.length">
          <div v-for="(cl, idx) in myCalls" :key="cl.call_id">
            <div v-if="idx > 0" class="call-divider"></div>
            <div class="call-card" :class="{ 'call-card-expanded': expandedCallId === cl.call_id }">
              <div class="call-card-header" @click="toggleCall(cl.call_id)">
                <div class="call-card-title-row">
                  <span class="call-card-title">{{ cl.title }}</span>
                  <span class="call-status-badge">{{ cl.status }}</span>
                </div>
                <div class="call-card-id-line">ID: {{ cl.call_id.slice(0, 18) }}...</div>
              </div>
              <div v-if="expandedCallId === cl.call_id" class="call-card-body">
                <div class="call-info-grid">
                  <div><strong>Descripción:</strong> {{ cl.description }}</div>
                  <div><strong>ID completo:</strong> <code>{{ cl.call_id }}</code></div>
                  <div v-if="cl.cfp_address"><strong>Contrato CFP:</strong> <code>{{ cl.cfp_address }}</code></div>
                  <div v-if="cl.creator"><strong>Creador:</strong> <code>{{ cl.creator }}</code></div>
                </div>
                <hr class="section-divider">
                <h4 class="proposals-title">Propuestas recibidas</h4>
                <div v-if="loadingProposals[cl.call_id]"><p>Cargando propuestas...</p></div>
                <div v-else-if="callProposals[cl.call_id] && callProposals[cl.call_id].length">
                  <div v-for="prop in callProposals[cl.call_id]" :key="prop.proposalId" class="proposal-card">
                    <div class="proposal-header">
                      <strong>{{ prop.title }}</strong>
                      <code class="proposal-id">{{ prop.proposalId.slice(0, 18) }}...</code>
                    </div>
                    <p class="proposal-desc">{{ prop.description }}</p>
                    <div v-if="prop.files && prop.files.length" class="proposal-files">
                      <strong>Archivos:</strong>
                      <ul class="file-list">
                        <li v-for="file in prop.files" :key="file.hash" class="file-item">
                          <a :href="getProposalDownloadUrl(prop.proposalId, file.hash)" download target="_blank" class="file-link">
                            <span class="file-icon">&#128206;</span>
                            {{ file.name }}
                          </a>
                          <span class="file-hash">{{ file.hash.slice(0, 18) }}...</span>
                        </li>
                      </ul>
                    </div>
                    <div v-else class="proposal-no-files">Sin archivos adjuntos.</div>
                  </div>
                </div>
                <div v-else>
                  <p class="no-proposals">No hay propuestas para este llamado.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else>
          <p>No has creado llamados aún.</p>
        </div>
        <button @click="loadMyCalls" :disabled="loadingCalls" class="reload-btn">Recargar llamados</button>
      </div>
      
      <p v-if="msg"><strong>{{ msg }}</strong></p>
    </div>
  </div>
</template>
<style scoped>
.call-divider {
  border: none;
  border-top: 2px solid #ddd;
  margin: 12px 0;
}

.call-card {
  border: 1px solid #ccc;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.call-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.call-card-expanded {
  box-shadow: 0 2px 12px rgba(0,0,0,0.12);
}

.call-card-header {
  padding: 12px 16px;
}

.call-card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.call-card-title {
  font-size: 1.2em;
  font-weight: 700;
}

.call-status-badge {
  font-size: 0.75em;
  background: #e8f5e9;
  color: #2e7d32;
  padding: 2px 10px;
  border-radius: 12px;
  text-transform: uppercase;
  font-weight: 600;
}

.call-card-id-line {
  font-size: 0.8em;
  color: #888;
  font-family: monospace;
}

.call-card-body {
  padding: 0 16px 16px;
  border-top: 1px dashed #e0e0e0;
}

.call-info-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.9em;
  margin-top: 10px;
}

.call-info-grid code {
  font-family: monospace;
  background: #f5f5f5;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.9em;
  word-break: break-all;
}

.section-divider {
  border: none;
  border-top: 1px solid #e0e0e0;
  margin: 14px 0;
}

.proposals-title {
  margin: 0 0 8px;
  font-size: 1em;
}

.proposal-card {
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
  background: #fafafa;
}

.proposal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.proposal-id {
  font-size: 0.75em;
  color: #999;
  font-family: monospace;
}

.proposal-desc {
  margin: 4px 0 8px;
  font-size: 0.9em;
  color: #555;
}

.proposal-files {
  margin-top: 6px;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 6px 0 0;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 4px;
  margin-bottom: 4px;
}

.file-link {
  text-decoration: none;
  color: #1976d2;
  font-weight: 500;
  font-size: 0.9em;
}

.file-link:hover {
  text-decoration: underline;
}

.file-icon {
  margin-right: 4px;
}

.file-hash {
  font-size: 0.75em;
  color: #aaa;
  font-family: monospace;
}

.proposal-no-files {
  font-size: 0.85em;
  color: #999;
  font-style: italic;
  margin-top: 4px;
}

.no-proposals {
  font-size: 0.9em;
  color: #888;
}

.reload-btn {
  margin-top: 10px;
  padding: 6px 16px;
  font-size: 0.85em;
}
</style>