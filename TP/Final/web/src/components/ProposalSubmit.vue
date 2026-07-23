<script setup>
import { ref, onMounted, inject } from 'vue'
import { Contract } from 'ethers'
import { useWallet } from '../composables/useWallet.js'
import { useApi } from '../composables/useApi.js'

const props = defineProps({
  callId: {
    type: String,
    required: true
  }
})

const api = useApi()
const { account, signer, isConnected } = useWallet()
const navigateTo = inject('navigateTo')
const title = ref('')
const description = ref('')
const files = ref([])
const msg = ref('')
const loading = ref(false)
const receiptGenerated = ref(null)
const requiresCollateral = ref(false)
const cfpAddress = ref('')
const guaranteeAmount = ref('0')
const callGuarantee = ref(0)
const userTokenBalance = ref(0n)
const tokenWarning = ref('')

onMounted(async () => {
  try {
    const res = await api.getCallGuarantee(props.callId)
    if (res.status === 200 && BigInt(res.data.guaranteeAmount || 0) > 0n) {
      callGuarantee.value = BigInt(res.data.guaranteeAmount)
      guaranteeAmount.value = String(callGuarantee.value)
      cfpAddress.value = res.data.cfp || ''
      if (isConnected.value && account.value) {
        const balRes = await api.getTokenBalance(account.value)
        userTokenBalance.value = BigInt(balRes.data.balance || 0)
        if (userTokenBalance.value < callGuarantee.value) {
          tokenWarning.value = `Necesitas al menos ${callGuarantee.value} tokens. Vas a la pestana Token, compra con ETH, y volve.`
        }
      }
    }
  } catch (e) {
    // llamado sin garantia o error
  }
})

const CFP_ABI = [
  'function registerProposalWithCollateral(bytes32 proposal)',
  'function guaranteeAmount() view returns (uint256)',
  'function token() view returns (address)',
]

const TOKEN_ABI = [
  'function approve(address spender, uint256 amount) returns (bool)',
]

function handleFileChange(event) {
  files.value = Array.from(event.target.files)
}

async function submitProposal() {
  if (!title.value || !description.value || files.value.length === 0) {
    msg.value = 'Debes completar título, descripción y adjuntar al menos un archivo.'
    return
  }
  loading.value = true
  msg.value = 'Enviando archivos al servidor...'
  try {
    const formData = new FormData()
    formData.append('callId', props.callId)
    formData.append('title', title.value)
    formData.append('description', description.value)
    if (account.value) formData.append('sender', account.value)
    for (const f of files.value) {
      formData.append('files', f)
    }
    
    const res = await api.postRegisterProposal(formData)
    if (res.status === 201) {
      // Verificar si el llamado requiere garantia
      if (res.data.requiresCollateral) {
        requiresCollateral.value = true
        cfpAddress.value = res.data.cfpAddress || ''
        guaranteeAmount.value = String(res.data.guaranteeAmount || 0)
        msg.value = 'Propuesta preparada. Abajo hace clic en "Aprobar tokens y registrar propuesta" y firma las 2 transacciones en MetaMask.'
        // Guardar datos para el paso 2
        receiptGenerated.value = {
          callId: props.callId,
          proposalId: res.data.proposalId,
          proof: res.data.proof,
          cfpAddress: res.data.cfpAddress,
          guaranteeAmount: res.data.guaranteeAmount,
          timestamp: new Date().toISOString()
        }
        downloadReceipt(receiptGenerated.value)
      } else {
        msg.value = '¡Propuesta registrada con éxito! Descargando tu recibo...'
        const receiptData = {
          callId: props.callId,
          proposalId: res.data.proposalId,
          proof: res.data.proof,
          timestamp: new Date().toISOString()
        }
        receiptGenerated.value = receiptData
        downloadReceipt(receiptData)
      }
    } else {
      msg.value = `Error de la API: ${res.data.message || 'Desconocido'}`
    }
  } catch (error) {
    msg.value = `Error al procesar: ${error.message}`
  } finally {
    loading.value = false
  }
}

async function approveAndRegisterWithCollateral() {
  if (!signer.value || !cfpAddress.value || !receiptGenerated.value) return
  loading.value = true
  msg.value = 'Paso 1/2: Aprobando transferencia de tokens...'
  try {
    const proposalId = receiptGenerated.value.proposalId
    const proposalBytes = proposalId

    // Encontrar la direccion del token desde el CFP
    const cfpContract = new Contract(cfpAddress.value, CFP_ABI, signer.value)
    const tokenAddr = await cfpContract.token()
    const amount = await cfpContract.guaranteeAmount()

    // Aprobar al CFP para gastar tokens
    const tokenContract = new Contract(tokenAddr, TOKEN_ABI, signer.value)
    const approveTx = await tokenContract.approve(cfpAddress.value, amount)
    msg.value = `Paso 1/2: Approve enviado: ${approveTx.hash}`
    await approveTx.wait()

    // Registrar propuesta con garantia
    msg.value = 'Paso 2/2: Registrando propuesta con garantia...'
    const tx = await cfpContract.registerProposalWithCollateral(proposalBytes)
    msg.value = `Paso 2/2: Transaccion enviada: ${tx.hash}`
    await tx.wait()
    msg.value = 'Propuesta registrada exitosamente con garantia.'
    requiresCollateral.value = false
  } catch (e) {
    msg.value = `Error: ${e.message}`
  } finally {
    loading.value = false
  }
}

function downloadReceipt(receiptObj) {
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(receiptObj, null, 2))
  const downloadAnchorNode = document.createElement('a')
  downloadAnchorNode.setAttribute("href",     dataStr)
  downloadAnchorNode.setAttribute("download", `recibo-${receiptObj.proposalId.substring(0, 8)}.json`)
  document.body.appendChild(downloadAnchorNode)
  downloadAnchorNode.click()
  downloadAnchorNode.remove()
}
</script>
<template>
  <div class="proposal-box">
    <h3>Presentar Propuesta</h3>
    
    <div v-if="tokenWarning && !receiptGenerated" class="token-warning">
      <p><strong>&#9888; Este llamado requiere garantia</strong></p>
      <p>{{ tokenWarning }}</p>
      <button @click="navigateTo('token')" class="btn-link">Ir a Token</button>
    </div>
    
    <div v-if="!receiptGenerated">
      <div>
        <label>Título:<br>
          <input v-model="title" placeholder="Título de tu propuesta" :disabled="loading" />
        </label>
      </div>
      <div>
        <label>Descripción:<br>
          <textarea v-model="description" placeholder="Descripción confidencial" :disabled="loading"></textarea>
        </label>
      </div>
      <div>
        <label>Archivos adjuntos:<br>
          <input type="file" multiple @change="handleFileChange" :disabled="loading" />
        </label>
      </div>
      
      <button @click="submitProposal" :disabled="loading">
        {{ loading ? 'Procesando...' : 'Obtener Recibo de Presentación' }}
      </button>
      
      <p class="feedback">{{ msg }}</p>
    </div>
    
    <div v-else-if="requiresCollateral" class="collateral-box">
      <h4>Propuesta Preparada</h4>
      <p>Este llamado requiere depositar <strong>{{ guaranteeAmount }}</strong> tokens como garantia.</p>
      <p>Pasos para completar:</p>
      <ol>
        <li><strong>Comprar tokens</strong> en la pestana Token si no tenes suficientes.</li>
        <li>Hacer clic en <strong>"Aprobar tokens y registrar propuesta"</strong> abajo.</li>
        <li>Firmar las <strong>2 transacciones</strong> en MetaMask:
          <br>1. <code>approve()</code> — autoriza al contrato a gastar tus tokens
          <br>2. <code>registerProposalWithCollateral()</code> — deposita la garantia y registra</li>
      </ol>
      <button @click="navigateTo('token')" class="btn-link">Ir a Token</button>
      <button @click="approveAndRegisterWithCollateral" :disabled="loading || !isConnected" class="btn-primary">
        {{ loading ? 'Procesando...' : 'Aprobar tokens y registrar propuesta' }}
      </button>
      <p class="feedback">{{ msg }}</p>
    </div>
    
    <div v-else class="success-box">
      <h4>¡Propuesta Sellada!</h4>
      <p>Tu recibo se ha descargado a tu computadora. Guárdalo bien junto con los archivos originales. Los necesitarás cuando la convocatoria cierre para entregar los archivos físicos.</p>
      <button @click="downloadReceipt(receiptGenerated)">Volver a descargar recibo</button>
    </div>
  </div>
</template>
<style scoped>
.proposal-box {
  background: var(--color-surface);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-top: var(--spacing-md);
}
.token-warning {
  background: #fff3e0;
  border: 1px solid #f0ad4e;
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}
.collateral-box {
  background: var(--color-surface);
  border: 1px solid #f0ad4e;
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-top: var(--spacing-md);
}
.collateral-box ol {
  margin: 8px 0;
  padding-left: 20px;
}
.collateral-box li {
  margin-bottom: 6px;
  font-size: 0.9em;
}
.btn-link {
  background: none;
  border: 1px solid #1976d2;
  color: #1976d2;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  margin-right: 8px;
  margin-bottom: 8px;
}
.btn-link:hover {
  background: #e3f2fd;
}
.btn-primary {
  background: #1976d2;
  color: #fff;
  border: none;
  padding: 8px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95em;
}
.success-box {
  background: var(--color-surface);
  border: 1px solid #4caf50;
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-top: var(--spacing-md);
}
</style>
