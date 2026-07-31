<script setup>
import { ref, onMounted, watch } from 'vue'
import { Contract } from 'ethers'
import { useWallet } from '../composables/useWallet.js'
import { useApi } from '../composables/useApi.js'

const api = useApi()
const { account, signer, isConnected } = useWallet()

const msg = ref('')
const myProposals = ref([])
const loadingProposals = ref(false)
const claiming = ref(false)

const CFP_ABI = [
  'function claimRefund(bytes32 proposal)',
  'function guaranteeAmount() view returns (uint256)',
  'function finalized() view returns (bool)',
  'function isProposalAccepted(bytes32) view returns (bool)',
  'function proposalData(bytes32) view returns (tuple(address sender, uint256 blockNumber, uint256 timestamp))',
]

onMounted(loadMyProposals)
watch(account, loadMyProposals)

async function loadMyProposals() {
  if (!account.value) return
  loadingProposals.value = true
  try {
    // GET /api/proposals?proponent=0x<cuenta>
    const res = await api.getProposals(account.value)
    const props = res.data.proposals || []
    myProposals.value = props
    checkProposalsStatus(props)
  } catch (e) {
    console.error('Error cargando propuestas:', e)
  } finally {
    loadingProposals.value = false
  }
}

async function checkProposalsStatus(proposals) {
  if (!signer.value || !signer.value.provider) {
    for (const p of proposals) {
      p._loadingStatus = false
      p._finalized = true
      p._accepted = false
    }
    return
  }
  const callCache = {}
  for (const p of proposals) {
    p._loadingStatus = true
    p._finalized = true
    p._accepted = false
    try {
      if (!callCache[p.call_id]) {
        const res = await api.getCallGuarantee(p.call_id)
        if (res.status !== 200) continue
        callCache[p.call_id] = { cfpAddr: res.data.cfp }
      }
      const { cfpAddr } = callCache[p.call_id]
      if (!cfpAddr) continue
      const cfpContract = new Contract(cfpAddr, CFP_ABI, signer.value)
      // Consulta on-chain si el llamado fue finalizado
      p._finalized = await cfpContract.finalized()
      if (p._finalized) {
        try {
          // Consulta on-chain si esta propuesta fue aceptada
          p._accepted = await cfpContract.isProposalAccepted(p.proposal_id)
        } catch {
          p._accepted = false
        }
      }
    } catch (e) {
      console.error('Error verificando estado de propuesta:', e)
    } finally {
      p._loadingStatus = false
    }
  }
}

// Reclama el reembolso de la garantia de una propuesta rechazada
async function doClaimRefund(callId, proposalId) {
  if (!signer.value) return
  claiming.value = true
  msg.value = 'Reclamando reembolso...'
  try {
    // Obtener direccion del CFP del llamado desde la API
    const res = await api.getCallGuarantee(callId)
    if (res.status !== 200) {
      msg.value = 'No se pudo obtener la informacion del llamado'
      return
    }
    const cfpAddr = res.data.cfp
    if (!cfpAddr) {
      msg.value = 'El llamado no tiene direccion CFP'
      return
    }
    // Instanciar el contrato CFP
    const cfpContract = new Contract(cfpAddr, CFP_ABI, signer.value)
    const tx = await cfpContract.claimRefund(proposalId)
    msg.value = `Reembolso enviado: ${tx.hash}. Esperando confirmacion...`
    await tx.wait()
    msg.value = 'Reembolso exitoso.'
    await loadMyProposals() // recargar para reflejar el cambio
  } catch (e) {
    msg.value = `Error: ${e.message}`
  } finally {
    claiming.value = false
  }
}
</script>

<template>
  <div>
    <h2>Reembolso de Garantia</h2>
    <p>Reclama el reembolso de tus tokens de garantia si tu propuesta no fue aceptada.</p>

    <hr>
    <h3>Mis Propuestas</h3>
    <div v-if="!isConnected"><p>Conecta tu wallet para ver tus propuestas.</p></div>
    <div v-else-if="loadingProposals"><p>Cargando propuestas...</p></div>
    <div v-else-if="!myProposals.length"><p>No tienes propuestas registradas.</p></div>
    <div v-else>
      <div v-for="p in myProposals" :key="p.proposal_id" class="proposal-card" :class="{ accepted: p._accepted }">
        <div class="prop-title">{{ p.title }}</div>
        <div class="prop-meta">
          <span><strong>Call ID:</strong> <code>{{ p.call_id }}</code></span>
          <span><strong>Proposal ID:</strong> <code>{{ p.proposal_id }}</code></span>
          <span v-if="p._loadingStatus" class="status loading">Verificando...</span>
          <span v-else-if="p._accepted" class="status accepted">Propuesta aceptada</span>
          <span v-else-if="p._finalized" class="status rejected">Propuesta rechazada</span>
        </div>
        <button
          v-if="p._finalized && !p._accepted"
          @click="doClaimRefund(p.call_id, p.proposal_id)"
          :disabled="claiming"
          class="btn-refund"
        >
          Reclamar Reembolso
        </button>
      </div>
    </div>

    <p v-if="msg" class="feedback">{{ msg }}</p>
  </div>
</template>

<style scoped>
.feedback {
  margin-top: 12px;
  font-weight: bold;
}
.proposal-card {
  background: var(--color-surface, #f9f9f9);
  border: 1px solid var(--color-border, #ccc);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
  transition: border-color 0.2s, background 0.2s;
}
.prop-title {
  font-weight: 700;
  margin-bottom: 4px;
}
.prop-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.85em;
  margin-bottom: 8px;
}
.prop-meta code {
  font-family: monospace;
  font-size: 0.85em;
  word-break: break-all;
  background: #f0f0f0;
  padding: 1px 4px;
  border-radius: 3px;
}
.btn-refund {
  padding: 6px 14px;
  font-size: 0.85em;
  cursor: pointer;
}
.status {
  font-size: 0.85em;
  font-weight: 600;
}
.status.loading {
  color: #888;
}
.status.accepted {
  color: #2e7d32;
}
.status.rejected {
  color: #c62828;
}
.proposal-card.accepted {
  border-color: #2e7d32;
  background: #e8f5e9;
}
</style>
