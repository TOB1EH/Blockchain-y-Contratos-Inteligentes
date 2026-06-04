<script setup>
import { ref, watch } from 'vue'
import { Contract } from 'ethers'
import { useWallet } from '../composables/useWallet.js'
import { useApi } from '../composables/useApi.js'
import { buildRegisterMessage, buildUpdateMessage } from '../utils/eip712.js'

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

// Definir ABI minima del factory para registro on-chain
const FACTORY_ABI = ['function register()']

// Verificar estado del creador al conectar cuenta
watch(account, async () => {
  msg.value = ''
  if (!account.value) { status.value = null; dbEntry.value = null; return }
  loadingStatus.value = true
  const addrRes = await api.getContractAddress()
  contractAddress.value = addrRes.data.address
  const regRes = await api.getRegistration(account.value)
  if (regRes.status === 200) {
    dbEntry.value = regRes.data
    // Si la API no devuelve 'name', significa que no estás en la base de datos
    if (!regRes.data.name) {
      status.value = 'none'
    } else {
      status.value = regRes.data.status
    }
  } else {
    status.value = 'none'
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
    msg.value = 'Registro on-chain exitoso. Ahora registrate off-chain.'
    const regRes = await api.getRegistration(account.value)
    // Si no hay 'name', seguimos forzando el estado 'none' para mostrar el formulario del Paso 2
    if (regRes.data && !regRes.data.name) {
      status.value = 'none'
    } else {
      status.value = regRes.data?.status || 'none'
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
      msg.value = `Registro off-chain exitoso. Estado: ${res.data.status}`
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
</script>

<template>
  <div>
    <h2>Panel de Creador</h2>
    <div v-if="!isConnected"><p>Conecta tu wallet para ver este panel.</p></div>
    <div v-else-if="loadingStatus"><p>Cargando estado...</p></div>
    <div v-else>
      <p><strong>Direccion:</strong> {{ account }}</p>
      <p><strong>Estado:</strong> {{ status || 'desconocido' }}</p>
      <div v-if="status === 'none'">
        <h3>Registro</h3>
        <p>Paso 1: Registrate on-chain (requiere firma MetaMask)</p>
        <button @click="registerOnChain">Registrarse on-chain</button>
        <hr>
        <p>Paso 2: Registrate off-chain en la API</p>
        <input v-model="name" placeholder="Nombre" />
        <button @click="registerOffChain">Registrarse off-chain</button>
      </div>
      <div v-else>
        <h3>Actualizar Perfil</h3>
        <p>Nombre actual: {{ dbEntry?.name }}</p>
        <input v-model="newName" placeholder="Nuevo nombre" />
        <button @click="updateProfile">Actualizar</button>
      </div>
      <p v-if="msg">{{ msg }}</p>
    </div>
  </div>
</template>
