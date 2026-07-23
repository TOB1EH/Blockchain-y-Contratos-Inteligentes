<script setup>
import { ref, onMounted } from 'vue'
import { Contract, keccak256, toUtf8Bytes } from 'ethers'
import { useWallet } from '../composables/useWallet.js'
import { useApi } from '../composables/useApi.js'

const api = useApi()
const { account, signer, isConnected } = useWallet()

const registryAddress = ref('')
const registrarAddress = ref('')
const resolverAddress = ref('')
const reverseRegistrarAddress = ref('')
const adminAddress = ref('')
const loading = ref(false)
const msg = ref('')

// Resolve directo
const resolveName = ref('')
const resolvedAddress = ref('')
const resolveMsg = ref('')

// Resolucion inversa
const reverseAddress = ref('')
const reversedName = ref('')
const forwardCheckOk = ref(false)
const reverseMsg = ref('')

// Autoregistro
const registerName = ref('')
const registerMsg = ref('')
const registering = ref(false)

const FIFS_ABI = [
  'function register(bytes32 label, address newOwner)',
  'function registry() view returns (address)',
  'function rootNode() view returns (bytes32)',
]

const REGISTRY_ABI = [
  'function setResolver(bytes32 node, address resolver)',
  'function resolver(bytes32 node) view returns (address)',
  'function owner(bytes32 node) view returns (address)',
]

const RESOLVER_ABI = [
  'function setAddr(bytes32 node, address addr)',
  'function addr(bytes32 node) view returns (address)',
]

const REVERSE_ABI = [
  'function setName(string memory name)',
]

onMounted(async () => {
  try {
    const [ensRes, adminRes] = await Promise.all([
      api.getEnsAddresses(),
      api.getAdminAddress()
    ])
    if (ensRes.status === 200) {
      registryAddress.value = ensRes.data.registry || ''
      registrarAddress.value = ensRes.data.registrar || ''
      resolverAddress.value = ensRes.data.resolver || ''
      reverseRegistrarAddress.value = ensRes.data.reverseRegistrar || ''
    }
    if (adminRes.status === 200) {
      adminAddress.value = adminRes.data.address
    }
  } catch (e) {
    msg.value = 'Error cargando direcciones ENS'
  }
})

async function doResolve() {
  if (!resolveName.value) return
  loading.value = true
  resolveMsg.value = ''
  resolvedAddress.value = ''
  try {
    const res = await api.postEnsResolve(resolveName.value)
    if (res.status === 200) {
      resolvedAddress.value = res.data.address
    } else {
      resolveMsg.value = res.data.message || 'No encontrado'
    }
  } catch (e) {
    resolveMsg.value = 'Error: ' + e.message
  } finally {
    loading.value = false
  }
}

async function doReverse() {
  if (!reverseAddress.value) return
  loading.value = true
  reverseMsg.value = ''
  reversedName.value = ''
  forwardCheckOk.value = false
  try {
    const res = await api.postEnsReverse(reverseAddress.value)
    if (res.status === 200) {
      reversedName.value = res.data.name
      // Verificar forward: resolver el nombre obtenido
      try {
        const fwd = await api.postEnsResolve(res.data.name)
        if (fwd.status === 200) {
          forwardCheckOk.value = fwd.data.address.toLowerCase() === reverseAddress.value.toLowerCase()
        }
      } catch (e) {
        forwardCheckOk.value = false
      }
      if (!forwardCheckOk.value) {
        reverseMsg.value = 'ADVERTENCIA: La resolucion directa no coincide. Posible impostura.'
      } else {
        reverseMsg.value = 'Verificacion exitosa: forward y reverse coinciden.'
      }
    } else {
      reverseMsg.value = res.data.message || 'No encontrado'
    }
  } catch (e) {
    reverseMsg.value = 'Error: ' + e.message
  } finally {
    loading.value = false
  }
}

async function doRegister() {
  if (!signer.value || !registerName.value || !registrarAddress.value) return
  if (account.value && adminAddress.value &&
      account.value.toLowerCase() === adminAddress.value.toLowerCase()) {
    registerMsg.value = 'La cuenta administradora no puede registrar nombres de usuario.'
    return
  }
  registering.value = true
  registerMsg.value = ''
  try {
    const name = registerName.value.trim()
    if (!name) {
      registerMsg.value = 'Ingresa un nombre valido'
      return
    }

    // 1. Registrar en FIFSRegistrar
    const label = keccak256(toUtf8Bytes(name))
    const fullName = name + '.usuarios.cfp'

    registerMsg.value = 'Paso 1/4: Registrando nombre en ENS...'
    const registrar = new Contract(registrarAddress.value, FIFS_ABI, signer.value)
    const tx1 = await registrar.register(label, account.value)
    registerMsg.value = 'Paso 1/4: Transaccion enviada, esperando confirmacion...'
    await tx1.wait()

    // 2. Configurar resolver
    registerMsg.value = 'Paso 2/4: Configurando resolver...'
    const registry = new Contract(registryAddress.value, REGISTRY_ABI, signer.value)
    const namehash = ethers_namehash(fullName)
    const tx2 = await registry.setResolver(namehash, resolverAddress.value)
    await tx2.wait()

    // 3. Configurar addr
    registerMsg.value = 'Paso 3/4: Configurando direccion...'
    const resolver = new Contract(resolverAddress.value, RESOLVER_ABI, signer.value)
    const tx3 = await resolver.setAddr(namehash, account.value)
    await tx3.wait()

    // 4. Configurar resolucion inversa
    registerMsg.value = 'Paso 4/4: Configurando resolucion inversa...'
    const reverseReg = new Contract(reverseRegistrarAddress.value, REVERSE_ABI, signer.value)
    const tx4 = await reverseReg.setName(fullName)
    await tx4.wait()

    registerMsg.value = `¡Registro exitoso! ${fullName} -> ${account.value}`
    registerName.value = ''
  } catch (e) {
    registerMsg.value = `Error: ${e.message}`
  } finally {
    registering.value = false
  }
}

function ethers_namehash(name) {
  const labels = name.split('.')
  let node = '0x' + '00'.repeat(32)
  for (let i = labels.length - 1; i >= 0; i--) {
    const labelHash = keccak256(toUtf8Bytes(labels[i]))
    node = keccak256(ethers_concat(node, labelHash))
  }
  return node
}

function ethers_concat(a, b) {
  const aBytes = a.startsWith('0x') ? a.slice(2) : a
  const bBytes = b.startsWith('0x') ? b.slice(2) : b
  return '0x' + aBytes + bBytes
}
</script>

<template>
  <div>
    <h2>Resolucion ENS</h2>
    <div v-if="!registryAddress"><p>ENS no configurado en la API.</p></div>
    <div v-else>

      <hr>
      <h3>Registrar mi nombre en usuarios.cfp</h3>
      <div v-if="!isConnected">
        <p>Conecta tu wallet para registrarte.</p>
      </div>
      <div v-else>
        <p>Tu direccion: <code>{{ account }}</code></p>
        <div v-if="account && adminAddress && account.toLowerCase() === adminAddress.toLowerCase()">
          <p class="feedback warn">La cuenta administradora no puede registrar nombres de usuario.<br>
          Usa una cuenta de MetaMask distinta (Account 1, 2, etc.).</p>
        </div>
        <div v-else>
          <div>
            <label>Nombre:<br>
              <input v-model="registerName" placeholder="ej: alice" :disabled="registering" />
              <small> Se registrara como <code>{{ registerName ? registerName + '.usuarios.cfp' : '...' }}</code></small>
            </label>
          </div>
          <button @click="doRegister" :disabled="registering || !registerName || !registrarAddress">
            {{ registering ? 'Registrando...' : 'Registrar en usuarios.cfp' }}
          </button>
        </div>
        <p v-if="registerMsg" :class="['feedback', registerMsg.includes('exitoso') ? 'ok' : '']">{{ registerMsg }}</p>
      </div>

      <hr>
      <h3>Resolver nombre a direccion</h3>
      <p>Ej: <code>alice.usuarios.cfp</code></p>
      <div>
        <input v-model="resolveName" placeholder="nombre.usuarios.cfp" />
        <button @click="doResolve" :disabled="loading || !resolveName">Resolver</button>
      </div>
      <p v-if="resolvedAddress">
        <strong>Direccion:</strong> <code>{{ resolvedAddress }}</code>
      </p>
      <p v-if="resolveMsg" class="feedback">{{ resolveMsg }}</p>

      <hr>
      <h3>Resolucion inversa (direccion a nombre)</h3>
      <div>
        <input v-model="reverseAddress" placeholder="0x..." />
        <button @click="doReverse" :disabled="loading || !reverseAddress">Resolver</button>
      </div>
      <p v-if="reversedName">
        <strong>Nombre:</strong> {{ reversedName }}
        <span v-if="forwardCheckOk" class="badge-ok">Verificado</span>
        <span v-else class="badge-warn">IMPOSTURA</span>
      </p>
      <p v-if="reverseMsg" :class="['feedback', forwardCheckOk ? 'ok' : '']">{{ reverseMsg }}</p>
    </div>
  </div>
</template>

<style scoped>
.feedback { margin-top: 8px; font-weight: bold; }
.feedback.ok { color: #2e7d32; }
.feedback.warn { color: #c62828; background: #fce4ec; padding: 8px; border-radius: 4px; }
.badge-ok { background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 4px; margin-left: 8px; font-size: 0.85em; font-weight: 600; }
.badge-warn { background: #fce4ec; color: #c62828; padding: 2px 8px; border-radius: 4px; margin-left: 8px; font-size: 0.85em; font-weight: 600; }
</style>
