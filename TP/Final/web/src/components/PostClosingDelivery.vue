<script setup>
import { ref } from 'vue'
import { useApi } from '../composables/useApi.js'

const api = useApi()
const receiptFile = ref(null)
const physicalFiles = ref([])
const msg = ref('')
const loading = ref(false)
const deliverySuccess = ref(false)
const deliveryReceipt = ref(null)

function handleReceiptChange(event) {
  receiptFile.value = event.target.files[0]
}

function handlePhysicalFilesChange(event) {
  physicalFiles.value = Array.from(event.target.files)
}

// Entrega de archivos y validación contra el recibo
async function deliverFiles() {
  if (!receiptFile.value || physicalFiles.value.length === 0) {
    msg.value = 'Debes subir tu recibo (.json) y al menos un archivo físico.'
    return
  }
  loading.value = true
  msg.value = 'Enviando archivos y validando integridad contra el recibo...'
  try {
    const text = await receiptFile.value.text()
    // Construir el FormData nativo para enviar multipart/form-data
    const formData = new FormData()
    formData.append('receipt', text) // Enviamos el JSON del recibo como string
    physicalFiles.value.forEach((file) => {
      formData.append('files', file) // Adjuntamos los archivos binarios
    })
    const res = await api.postDeliver(formData)
    if (res.status === 201) {
      deliveryReceipt.value = res.data
      msg.value = '¡Archivos entregados y registrados en la blockchain con éxito!'
      deliverySuccess.value = true
    } else {
      msg.value = `Error en la entrega: ${res.data.message}`
    }
  } catch (error) {
    msg.value = `Error inesperado: ${error.message}`
  } finally {
    loading.value = false
  }
}

function downloadDeliveryReceipt() {
  if (!deliveryReceipt.value) return
  const blob = new Blob([JSON.stringify(deliveryReceipt.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `delivery-receipt-${deliveryReceipt.value.proposalId}.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
<template>
  <div class="delivery-box">
    <h3>Entrega Definitiva (Post-Cierre)</h3>
    <p>Sube tu recibo de presentación original y los archivos físicos exactos que comprometiste. La API verificará matemáticamente que nadie haya alterado ni un solo byte.</p>
    
    <div v-if="!deliverySuccess">
      <div>
        <label>1. Sube tu recibo (.json):<br>
          <input type="file" accept="application/json" @change="handleReceiptChange" :disabled="loading" />
        </label>
      </div>
      <div style="margin-top: 10px;">
        <label>2. Sube tus archivos físicos originales:<br>
          <input type="file" multiple @change="handlePhysicalFilesChange" :disabled="loading" />
        </label>
      </div>
      
      <button @click="deliverFiles" :disabled="loading || !receiptFile || physicalFiles.length === 0" style="margin-top: 15px;">
        {{ loading ? 'Transfiriendo y Sellando...' : 'Entregar Archivos Definitivos' }}
      </button>
      
      <p class="feedback">{{ msg }}</p>
    </div>
    
    <div v-else class="success-box">
      <h4>¡Entrega Validada y Sellada!</h4>
      <p>La API confirmó matemáticamente que tus archivos son idénticos a los comprometidos inicialmente y registró un comprobante criptográfico en el contrato inteligente del llamado.</p>
      <ul v-if="deliveryReceipt">
        <li><strong>ID Propuesta:</strong> {{ deliveryReceipt.proposalId }}</li>
        <li><strong>FilesRoot:</strong> {{ deliveryReceipt.filesRoot }}</li>
        <li><strong>TxHash:</strong> {{ deliveryReceipt.txHash }}</li>
        <li><strong>Bloque:</strong> {{ deliveryReceipt.blockNumber }}</li>
      </ul>
      <p style="margin-top: 10px;">Archivos entregados exitosamente al creador del llamado.</p>
      <button @click="downloadDeliveryReceipt" style="margin-top: 10px;">
        Descargar Recibo de Entrega
      </button>
    </div>
  </div>
</template>
<style scoped>
.delivery-box {
  background: var(--color-warning-light);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-top: var(--spacing-md);
}
</style>