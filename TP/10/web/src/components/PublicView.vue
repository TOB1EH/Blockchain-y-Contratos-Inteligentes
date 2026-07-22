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
const callDeliveries = ref({}) // Almacena entregas visibles publicamente
const loadingDeliveries = ref({})

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
  
  if (action === 'deliveries') {
    loadCallDeliveries(callId)
  }
}

// Cargar entregas publicas de un llamado cerrado
async function loadCallDeliveries(callId) {
  if (callDeliveries.value[callId]) return
  loadingDeliveries.value = { ...loadingDeliveries.value, [callId]: true }
  try {
    const res = await api.getCallDeliveries(callId)
    callDeliveries.value = { ...callDeliveries.value, [callId]: res.data.deliveries || [] }
  } catch (e) {
    console.error(e)
  } finally {
    loadingDeliveries.value = { ...loadingDeliveries.value, [callId]: false }
  }
}
function getDeliveryDownloadUrl(proposalId, fileHash) {
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
              <button v-if="!isCallOpen(cl.call_id)" @click="openAction(cl.call_id, 'deliveries')" class="btn-outline">
                Ver Entregas
              </button>
            </div>
          </div>
        </div>
        <!-- Renderizado dinámico según la acción seleccionada para este llamado -->
        <div v-if="activeCallId === cl.call_id" class="action-panel">
          <ProposalSubmit v-if="activeAction === 'submit'" :callId="cl.call_id" />
          
          <PostClosingDelivery v-if="activeAction === 'deliver'" />
          <div v-if="activeAction === 'deliveries'" class="deliveries-panel">
            <h4>Archivos recibidos (post-cierre)</h4>
            <div v-if="loadingDeliveries[cl.call_id]"><p>Cargando entregas...</p></div>
            <div v-else-if="callDeliveries[cl.call_id] && callDeliveries[cl.call_id].length">
              <div v-for="del in callDeliveries[cl.call_id]" :key="del.proposal_id" class="public-proposal-card">
                <div class="public-proposal-header">
                  <strong>Propuesta {{ del.proposal_id.slice(0, 18) }}...</strong>
                  <span class="delivery-date">Entregado: {{ del.delivered_at }}</span>
                </div>
                <p><strong>Sender:</strong> <code>{{ del.sender }}</code></p>
                <p><strong>Files Root:</strong> <code>{{ del.files_root }}</code></p>
                <div v-if="del.files && del.files.length" class="public-proposal-files">
                  <strong>Archivos:</strong>
                  <ul class="public-file-list">
                    <li v-for="file in del.files" :key="file.file_hash" class="public-file-item">
                      <a :href="getDeliveryDownloadUrl(del.proposal_id, file.file_hash)" download target="_blank" class="public-file-link">
                        <span class="file-icon">&#128206;</span>
                        {{ file.file_name }}
                      </a>
                      <span class="file-hash-label">{{ file.file_hash.slice(0, 18) }}...</span>
                    </li>
                  </ul>
                </div>
                <div v-else class="public-proposal-no-files">Sin archivos adjuntos.</div>
              </div>
            </div>
            <div v-else>
              <p>No hay entregas para este llamado.</p>
            </div>
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

.deliveries-panel {
  margin-top: 10px;
}

.delivery-date {
  font-size: 0.8em;
  color: #888;
}

.public-proposal-card {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
  background: #fafafa;
}

.public-proposal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.proposal-id-label {
  font-size: 0.75em;
  color: #999;
  font-family: monospace;
}

.public-proposal-desc {
  margin: 4px 0 8px;
  font-size: 0.9em;
  color: #555;
}

.public-proposal-files {
  margin-top: 6px;
}

.public-file-list {
  list-style: none;
  padding: 0;
  margin: 6px 0 0;
}

.public-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 4px;
  margin-bottom: 4px;
}

.public-file-link {
  text-decoration: none;
  color: #1976d2;
  font-weight: 500;
  font-size: 0.9em;
}

.public-file-link:hover {
  text-decoration: underline;
}

.file-icon {
  margin-right: 4px;
}

.file-hash-label {
  font-size: 0.75em;
  color: #aaa;
  font-family: monospace;
}

.public-proposal-no-files {
  font-size: 0.85em;
  color: #999;
  font-style: italic;
  margin-top: 4px;
}
</style>