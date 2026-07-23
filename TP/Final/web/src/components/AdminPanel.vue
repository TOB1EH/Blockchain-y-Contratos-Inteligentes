<script setup>
import { ref, watch } from 'vue'
import { useWallet } from '../composables/useWallet.js'
import { useApi } from '../composables/useApi.js'
import { buildAuthorizeMessage, buildUnauthorizeMessage } from '../utils/eip712.js'

// Declarar estado reactivo del panel de administrador
const api = useApi()
const { account, signer, chainId, isConnected } = useWallet()

const adminAddress = ref('')
const contractAddress = ref('')
const pending = ref([])
const isAdmin = ref(false)
const msg = ref('')
const loading = ref(false)

// Verificar rol admin y obtener solicitudes pendientes
watch(account, async () => {
  msg.value = ''
  if (!account.value) { isAdmin.value = false; return }
  const [addrRes, pendingRes, adminRes] = await Promise.all([
    api.getContractAddress(),
    api.getPendingCreators(),
    api.getAdminAddress(),
  ])
  contractAddress.value = addrRes.data.address
  adminAddress.value = adminRes.data.address
  isAdmin.value = account.value.toLowerCase() === adminAddress.value.toLowerCase()
  pending.value = pendingRes.data.pending || []
}, { immediate: true })

// Firmar y enviar autorizacion de creador via EIP-712
async function authorize(target) {
  if (!signer.value || !contractAddress.value) return
  try {
    const nonceRes = await api.getAdminNonce()
    const nonce = nonceRes.data.nonce
    const typedData = buildAuthorizeMessage(chainId.value, contractAddress.value, nonce, target)
    const signature = await signer.value.signTypedData(
      typedData.domain, typedData.types, typedData.message
    )
    const res = await api.postAuthorize(target, signature)
    if (res.status === 200) {
      msg.value = `Autorizado: ${target}`
      pending.value = pending.value.filter(c => c.address !== target)
    } else {
      msg.value = `Error: ${res.data.message}`
    }
  } catch (e) {
    msg.value = `Error: ${e.message}`
  }
}

// Firmar y enviar desautorizacion de creador via EIP-712
async function unauthorize(target) {
  if (!signer.value || !contractAddress.value) return
  try {
    const nonceRes = await api.getAdminNonce()
    const nonce = nonceRes.data.nonce
    const typedData = buildUnauthorizeMessage(chainId.value, contractAddress.value, nonce, target)
    const signature = await signer.value.signTypedData(
      typedData.domain, typedData.types, typedData.message
    )
    const res = await api.postUnauthorize(target, signature)
    if (res.status === 200) {
      msg.value = `Desautorizado: ${target}`
      pending.value = pending.value.filter(c => c.address !== target)
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
    <h2>Panel de Administrador</h2>
    <div v-if="!isConnected"><p>Conecta tu wallet para ver este panel.</p></div>
    <div v-else-if="!isAdmin"><p>La cuenta conectada no es administradora (admin: {{ adminAddress }}).</p></div>
    <div v-else>
      <h3>Solicitudes pendientes ({{ pending.length }})</h3>
      <table v-if="pending.length">
        <thead>
          <tr><th>Dirección</th><th>Nombre</th><th>Acción</th></tr>
        </thead>
        <tbody>
          <tr v-for="c in pending" :key="c.address">
            <td>{{ c.address }}</td>
            <td>{{ c.name }}</td>
            <td>
              <button @click="authorize(c.address)">Autorizar</button>
              <button @click="unauthorize(c.address)">Desautorizar</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else>No hay solicitudes pendientes.</p>
      <p v-if="msg">{{ msg }}</p>
    </div>
  </div>
</template>
