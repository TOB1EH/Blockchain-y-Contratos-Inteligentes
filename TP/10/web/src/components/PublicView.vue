<script setup>
import { ref, onMounted, computed } from 'vue'
import { useApi } from '../composables/useApi.js'
import ProposalSubmit from './ProposalSubmit.vue'
import ReceiptVerifier from './ReceiptVerifier.vue'
import PostClosingDelivery from './PostClosingDelivery.vue'

const api = useApi()
const creators = ref([])
const calls = ref([])
const loadingCreators = ref(true)
const loadingCalls = ref(true)
const filterCreator = ref('')

// Estados de interfaz para modales/vistas expandidas
const showVerifier = ref(false)
const activeCallId = ref(null)
const activeAction = ref(null) // 'submit', 'deliver', 'files'
const callClosingTimes = ref({})
const callFiles = ref({}) // Almacena archivos descargables por proposalId

onMounted(async () => {
  const [cr, cl] = await Promise.all([
    api.getCreators(),
    api.getCalls()
  ])
  creators.value = cr.data.creators || []
  calls.value = cl.data.calls || []
  loadingCreators.value = false
  loadingCalls.value = false
  // Consultar tiempos de cierre para todos los llamados
  for (const c of calls.value) {
    try {
      // Usamos fetch directamente porque getClosingTime no está en useApi
      const res = await fetch(`/api/closing-time/${c.call_id}`)
      if (res.ok) {
        const data = await res.json()
        callClosingTimes.value[c.call_id] = new Date(data.closingTime)
      }
    } catch (e) {
      console.error(`Error obteniendo closingTime para ${c.call_id}`)
    }
  }
})

const filteredCalls = computed(() => {
  if (!filterCreator.value) return calls.value
  return calls.value.filter(c => c.creator && c.creator.toLowerCase() === filterCreator.value.toLowerCase())
})

function selectCreator(creatorAddress) {
  filterCreator.value = creatorAddress === filterCreator.value ? '' : creatorAddress
}

function isCallOpen(callId) {
  const closingTime = callClosingTimes.value[callId]
  if (!closingTime) return false
  return new Date() <= closingTime
}

function openAction(callId, action) {
  activeCallId.value = activeCallId.value === callId && activeAction.value === action ? null : callId
  activeAction.value = activeCallId.value ? action : null
  
  if (action === 'files') {
    loadFilesForCall(callId)
  }
}

// Nota: en una app real habría un endpoint para buscar deliveries por call_id. 
// Aquí lo simulamos requiriendo que el usuario ingrese el proposal_id para ver los archivos.
const searchProposalId = ref('')
const filesLoadMsg = ref('')
async function loadFilesForCall() {
  if (!searchProposalId.value) return
  filesLoadMsg.value = 'Buscando archivos...'
  callFiles.value = {}
  try {
    const res = await api.getDeliveryInfo(searchProposalId.value)
    if (res.status === 200) {
      callFiles.value[searchProposalId.value] = res.data.files
      filesLoadMsg.value = 'Archivos encontrados:'
    } else {
      filesLoadMsg.value = 'No se encontró entrega para este ID o aún no se han subido archivos.'
    }
  } catch (e) {
    filesLoadMsg.value = 'Error al buscar archivos.'
  }
}
function getDownloadUrl(proposalId, fileHash) {
  return `/api/deliveries/${proposalId}/files/${fileHash}`
}
</script>
<template>
  <div>
    <div class="header-actions">
      <button @click="showVerifier = !showVerifier" class="btn-verify">
        {{ showVerifier ? 'Cerrar Verificador' : 'Abrir Verificador de Recibos' }}
      </button>
    </div>
    <ReceiptVerifier v-if="showVerifier" />
    <hr>
    <h2>Creadores registrados</h2>
    <div v-if="loadingCreators">Cargando...</div>
    <table v-else-if="creators.length">
      <thead>
        <tr>
          <th>Dirección</th>
          <th>Nombre</th>
          <th>Estado</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in creators" :key="c.address" :class="{ selected: filterCreator === c.address }">
          <td>{{ c.address }}</td>
          <td>{{ c.name }}</td>
          <td>{{ c.status }}</td>
          <td><button @click="selectCreator(c.address)">Ver llamados</button></td>
        </tr>
      </tbody>
    </table>
    <p v-else>No hay creadores registrados.</p>
    <h2 v-if="filterCreator">Llamados de {{ filterCreator }}</h2>
    <h2 v-else>Llamados globales</h2>
    <div v-if="loadingCalls">Cargando llamados...</div>
    
    <div v-else-if="filteredCalls.length">
      <div v-for="cl in filteredCalls" :key="cl.call_id" class="call-card">
        <div class="call-header">
          <div>
            <h4>{{ cl.title }}</h4>
            <p class="desc">{{ cl.description }}</p>
            <small><strong>Creador:</strong> {{ cl.creator }}</small>
            <br>
            <small><strong>ID:</strong> {{ cl.call_id }}</small>
          </div>
          <div class="call-status">
            <span :class="['badge', isCallOpen(cl.call_id) ? 'badge-open' : 'badge-closed']">
              {{ isCallOpen(cl.call_id) ? 'ABIERTO' : 'CERRADO' }}
            </span>
            <div class="call-actions">
              <button v-if="isCallOpen(cl.call_id)" @click="openAction(cl.call_id, 'submit')" class="btn-primary">
                Presentar Propuesta
              </button>
              <button v-else @click="openAction(cl.call_id, 'deliver')" class="btn-secondary">
                Entregar Archivos
              </button>
              <button v-if="!isCallOpen(cl.call_id)" @click="openAction(cl.call_id, 'files')" class="btn-outline">
                Ver Archivos
              </button>
            </div>
          </div>
        </div>
        <!-- Renderizado dinámico según la acción seleccionada para este llamado -->
        <div v-if="activeCallId === cl.call_id" class="action-panel">
          <ProposalSubmit v-if="activeAction === 'submit'" :callId="cl.call_id" />
          
          <PostClosingDelivery v-if="activeAction === 'deliver'" />
          <div v-if="activeAction === 'files'" class="files-panel">
            <h4>Archivos Públicos</h4>
            <p>Ingresa el ID de la propuesta (proposalId) para descargar sus archivos:</p>
            <input v-model="searchProposalId" placeholder="0x..." style="width: 300px;" />
            <button @click="loadFilesForCall">Buscar</button>
            <p>{{ filesLoadMsg }}</p>
            <ul v-if="callFiles[searchProposalId]">
              <li v-for="file in callFiles[searchProposalId]" :key="file.hash">
                <a :href="getDownloadUrl(searchProposalId, file.hash)" download target="_blank">
                  📄 {{ file.name }}
                </a>
                <br>
                <small>Hash: {{ file.hash }}</small>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
    <p v-else>No hay llamados disponibles.</p>
  </div>
</template>
<style scoped>
.header-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--spacing-md);
}

.call-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  box-shadow: var(--shadow-sm);
}

.call-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-md);
}

.call-status {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  align-items: flex-end;
}

.call-actions {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.action-panel {
  margin-top: var(--spacing-md);
  border-top: 1px dashed var(--color-border);
  padding-top: var(--spacing-md);
}

.files-panel {
  background: #fafafa;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-top: var(--spacing-sm);
}
</style>