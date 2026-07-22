<script setup>
import { ref } from 'vue'
import { useApi } from '../composables/useApi.js'

const props = defineProps({
  callId: {
    type: String,
    required: true
  }
})

const api = useApi()
const title = ref('')
const description = ref('')
const files = ref([])
const msg = ref('')
const loading = ref(false)
const receiptGenerated = ref(null)

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
    for (const f of files.value) {
      formData.append('files', f)
    }
    
    const res = await api.postRegisterProposal(formData)
    if (res.status === 201) {
      msg.value = '¡Propuesta registrada con éxito! Descargando tu recibo...'
      
      const receiptData = {
        callId: props.callId,
        proposalId: res.data.proposalId,
        proof: res.data.proof,
        timestamp: new Date().toISOString()
      }
      
      receiptGenerated.value = receiptData
      downloadReceipt(receiptData)
    } else {
      msg.value = `Error de la API: ${res.data.message || 'Desconocido'}`
    }
  } catch (error) {
    msg.value = `Error al procesar: ${error.message}`
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
    <h3>Presentar Propuesta (Anónimo)</h3>
    <p>Esta acción es anónima y no requiere MetaMask. Tus archivos se almacenan de forma segura en el servidor hasta que la convocatoria cierre.</p>
    
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
</style>
