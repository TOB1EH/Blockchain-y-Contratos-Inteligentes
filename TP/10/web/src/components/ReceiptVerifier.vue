<script setup>
import { ref } from 'vue'
import { Contract } from 'ethers'
import { useWallet } from '../composables/useWallet.js'
import { useApi } from '../composables/useApi.js'

const api = useApi()
const { signer } = useWallet()
const receiptFile = ref(null)
const verificationResult = ref(null)
const errorMsg = ref('')
const loading = ref(false)

// ABIs para verificar on-chain
const CFP_ABI = [
  'function proposalData(bytes32 proposal) view returns (tuple(address sender, uint256 blockNumber, uint256 timestamp))',
  'function deliveryData(bytes32 proposal) view returns (tuple(address sender, uint256 blockNumber, uint256 timestamp, bytes32 filesRoot, bool delivered))'
]

const FACTORY_ABI = [
  'function calls(bytes32 callId) view returns (tuple(address creator, address cfp))'
]

function handleReceiptUpload(event) {
  receiptFile.value = event.target.files[0]
  verificationResult.value = null
  errorMsg.value = ''
}

async function verifyReceipt() {
  if (!receiptFile.value) {
    errorMsg.value = 'Debes subir un archivo de recibo (.json)'
    return
  }
  loading.value = true
  errorMsg.value = ''
  verificationResult.value = null
  try {
    // 1. Leer el archivo JSON localmente
    const text = await receiptFile.value.text()
    const receipt = JSON.parse(text)

    // Detectar tipo de recibo: proposal (con proof) o delivery (con txHash/filesRoot)
    const isDeliveryReceipt = receipt.txHash && receipt.filesRoot && !receipt.proof
    const isProposalReceipt = receipt.proposalId && receipt.callId && receipt.proof

    if (!isProposalReceipt && !isDeliveryReceipt) {
      throw new Error("El archivo no tiene un formato de recibo válido (proposal o delivery).")
    }

    if (isProposalReceipt) {
      // 2a. Verificación Matemática contra la API
      const leaves = Object.keys(receipt.proof)
      if (leaves.length === 0) throw new Error("El recibo no contiene pruebas de Merkle.")
      
      const testLeaf = leaves[0]
      const testProof = receipt.proof[testLeaf]
      const apiRes = await api.postVerifyProof(receipt.proposalId, testLeaf, testProof)
      if (apiRes.status !== 200 || !apiRes.data.valid) {
        throw new Error("La validación matemática falló. El recibo está alterado o es falso.")
      }
    }

    // 3. Verificación On-Chain
    let onChainStatus = "No verificable sin MetaMask conectado"
    if (signer.value) {
      const addrRes = await api.getContractAddress()
      const factory = new Contract(addrRes.data.address, FACTORY_ABI, signer.value)
      
      // Obtener callId del recibo (proposal lo tiene, delivery no)
      let callId = receipt.callId
      if (!callId) {
        const propInfo = await api.getDeliveryInfo(receipt.proposalId)
        if (propInfo.status !== 200) {
          throw new Error("No se pudo encontrar la propuesta asociada al recibo de entrega.")
        }
        callId = propInfo.data.callId
        if (!callId) {
          throw new Error("No se pudo determinar el callId de la propuesta.")
        }
      }

      const callData = await factory.calls(callId)
      if (callData.cfp === '0x0000000000000000000000000000000000000000') {
        throw new Error("El llamado asociado a este recibo no existe en la blockchain.")
      }
      const cfp = new Contract(callData.cfp, CFP_ABI, signer.value)
      
      if (isDeliveryReceipt) {
        // Verificar entrega post-cierre
        const delData = await cfp.deliveryData(receipt.proposalId)
        if (delData.delivered) {
          onChainStatus = `Archivos recibidos en el Bloque #${delData.blockNumber.toString()}. FilesRoot: ${delData.filesRoot}`
        } else {
          throw new Error("La entrega NO está registrada en la blockchain.")
        }
      } else {
        // Verificar propuesta
        const propData = await cfp.proposalData(receipt.proposalId)
        if (propData.blockNumber > 0n) {
          onChainStatus = `Confirmado inmutable en el Bloque #${propData.blockNumber.toString()}`
        } else {
          throw new Error("Alerta: La propuesta NO está registrada en la blockchain.")
        }
      }
    }
    verificationResult.value = {
      proposalId: receipt.proposalId,
      callId: receipt.callId || 'No disponible',
      onChainStatus,
      type: isDeliveryReceipt ? 'delivery' : 'proposal'
    }
  } catch (err) {
    errorMsg.value = err.message
  } finally {
    loading.value = false
  }
}

</script>
<template>
  <div class="verifier-box">
    <h3>Verificador de Recibos Criptográficos</h3>
    <p>Sube tu archivo de recibo (.json) para verificar matemáticamente que tu propuesta es auténtica y está sellada en la blockchain.</p>
    
    <div>
      <input type="file" accept="application/json" @change="handleReceiptUpload" :disabled="loading" />
    </div>
    <button @click="verifyReceipt" :disabled="loading || !receiptFile" style="margin-top: 10px;">
      {{ loading ? 'Auditando...' : 'Verificar Recibo' }}
    </button>
    <div v-if="errorMsg" class="error-msg">
      {{ errorMsg }}
    </div>
    <div v-if="verificationResult" class="success-box">
      <h4>{{ verificationResult.type === 'delivery' ? 'Recibo de Entrega Válido' : 'Recibo Válido y Auténtico' }}</h4>
      <ul>
        <li><strong>ID Propuesta:</strong> {{ verificationResult.proposalId }}</li>
        <li><strong>Llamado:</strong> {{ verificationResult.callId }}</li>
        <li v-if="verificationResult.type === 'proposal'"><strong>Prueba de Merkle:</strong> Válida (Verificada por la API)</li>
        <li><strong>Estado en Blockchain:</strong> {{ verificationResult.onChainStatus }}</li>
      </ul>
    </div>
  </div>
</template>
<style scoped>
.verifier-box {
  background: var(--color-info-light);
  border: 1px solid var(--color-info);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-top: var(--spacing-md);
}
</style>