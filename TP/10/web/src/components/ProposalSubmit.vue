<script setup>
import { ref } from 'vue'
import { keccak256 } from 'ethers'
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

// Manejar selección de archivos
function handleFileChange(event) {
  files.value = Array.from(event.target.files)
}

// Calcular hash de un archivo localmente usando FileReader y keccak256
function computeFileHash(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const buffer = new Uint8Array(e.target.result)
      const hash = keccak256(buffer)
      resolve(hash)
    }
    reader.onerror = (e) => reject(e)
    reader.readAsArrayBuffer(file)
  })
}

async function submitProposal() {
  if (!title.value || !description.value || files.value.length === 0) {
    msg.value = 'Debes completar título, descripción y adjuntar al menos un archivo.'
    return
  }
  loading.value = true
  msg.value = 'Calculando hashes localmente (tus archivos no se envían al servidor)...'
  try {
    // 1. Calcular hashes de todos los archivos seleccionados
    const fileHashes = await Promise.all(files.value.map(f => computeFileHash(f)))
    
    msg.value = 'Hashes calculados. Generando compromiso on-chain a través de la API...'
    // 2. Enviar título, descripción y HASHES a la API
    const res = await api.postRegisterProposal(props.callId, title.value, description.value, fileHashes)
    if (res.status === 201) {
      msg.value = '¡Propuesta registrada con éxito! Descargando tu recibo...'
      
      // 3. Preparar el recibo (JSON) para descargar
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

// Forzar descarga del JSON
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
    <p>Esta acción es anónima y no requiere MetaMask. Los archivos originales permanecerán en tu computadora hasta que la convocatoria cierre.</p>
    
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
  border: 1px solid #ccc;
  padding: 15px;
  margin-top: 15px;
  border-radius: 5px;
  background-color: #f9f9f9;
}
.feedback {
  font-weight: bold;
  color: #333;
}
.success-box {
  background-color: #e8f5e9;
  padding: 10px;
  border: 1px solid #c8e6c9;
  border-radius: 4px;
}
</style>