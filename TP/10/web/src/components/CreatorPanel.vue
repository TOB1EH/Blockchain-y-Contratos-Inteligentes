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
const closingDays = ref(7)
const creatingCall = ref(false)

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
    await tx.wait()
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
    const closingTimestamp = Math.floor(Date.now() / 1000) + closingDays.value * 86400
    const contract = new Contract(contractAddress.value, FACTORY_ABI, signer.value)
    const tx = await contract.create(callId, closingTimestamp)
    msg.value = `Paso 2/2: Transaccion enviada: ${tx.hash}. Esperando confirmacion...`
    await tx.wait()
    msg.value = `Llamado creado exitosamente. La cadena lo confirmara en breve.`
    callTitle.value = ''
    callDescription.value = ''
    closingDays.value = 7
  } catch (e) {
    msg.value = `Error: ${e.message}`
  } finally {
    creatingCall.value = false
  }
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
          <label>Días hasta el cierre:<br><input v-model.number="closingDays" type="number" min="1" max="365" :disabled="creatingCall" /></label>
        </div>
        <button @click="createCall" :disabled="creatingCall || !callTitle || !callDescription">
          {{ creatingCall ? 'Creando llamado...' : 'Crear Llamado' }}
        </button>
      </div>
      
      <p v-if="msg"><strong>{{ msg }}</strong></p>
    </div>
  </div>
</template>