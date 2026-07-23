<script setup>
import { ref, onMounted, watch } from 'vue'
import { Contract, parseEther } from 'ethers'
import { useWallet } from '../composables/useWallet.js'
import { useApi } from '../composables/useApi.js'

const api = useApi()
const { account, signer, isConnected } = useWallet()

const tokenAddress = ref('')
const tokenName = ref('')
const tokenSymbol = ref('')
const tokensPerEth = ref(0n)
const decimals = ref(18)
const balance = ref(0n)
const msg = ref('')
const loading = ref(false)

const TOKEN_ABI = [
  'function name() view returns (string)',
  'function symbol() view returns (string)',
  'function decimals() view returns (uint8)',
  'function balanceOf(address) view returns (uint256)',
  'function buy() payable',
  'function redeem(uint256 amount)',
  'function tokensPerEth() view returns (uint256)',
  'function approve(address spender, uint256 amount) returns (bool)',
]

async function loadTokenInfo() {
  try {
    const addrRes = await api.getTokenAddress()
    tokenAddress.value = addrRes.data.address || ''

    const nameRes = await api.getTokenName()
    tokenName.value = nameRes.data.name || ''
    tokenSymbol.value = nameRes.data.symbol || ''
    tokensPerEth.value = BigInt(nameRes.data.tokensPerEth || 0)
    decimals.value = nameRes.data.decimals || 18

    if (account.value && tokenAddress.value) {
      await refreshBalance()
    }
  } catch (e) {
    msg.value = 'Token no disponible: ' + e.message
  }
}

async function refreshBalance() {
  if (!account.value || !tokenAddress.value) return
  try {
    const balRes = await api.getTokenBalance(account.value)
    balance.value = BigInt(balRes.data.balance || 0)
  } catch (e) {
    console.error('Error obteniendo balance:', e)
  }
}

onMounted(loadTokenInfo)
watch(account, loadTokenInfo)

async function buyTokens() {
  if (!signer.value || !tokenAddress.value) return
  loading.value = true
  msg.value = 'Enviando transaccion...'
  try {
    const contract = new Contract(tokenAddress.value, TOKEN_ABI, signer.value)
    const tx = await contract.buy({ value: parseEther('0.1') })
    msg.value = `Compra enviada: ${tx.hash}`
    await tx.wait()
    msg.value = 'Tokens comprados exitosamente.'
    await refreshBalance()
  } catch (e) {
    msg.value = `Error: ${e.message}`
  } finally {
    loading.value = false
  }
}

async function redeemTokens() {
  if (!signer.value || !tokenAddress.value || balance.value <= 0n) return
  loading.value = true
  msg.value = 'Enviando transaccion...'
  try {
    const contract = new Contract(tokenAddress.value, TOKEN_ABI, signer.value)
    const tx = await contract.redeem(balance.value)
    msg.value = `Redencion enviada: ${tx.hash}`
    await tx.wait()
    msg.value = 'Tokens redimidos exitosamente.'
    await refreshBalance()
  } catch (e) {
    msg.value = `Error: ${e.message}`
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h2>Token de Gobernanza</h2>
    <div v-if="!tokenAddress"><p>Token no configurado en la API.</p></div>
    <div v-else>
      <table class="info-table">
        <tr><td>Nombre:</td><td>{{ tokenName }} ({{ tokenSymbol }})</td></tr>
        <tr><td>Precio:</td><td>1 ETH = {{ tokensPerEth.toString() }} {{ tokenSymbol }}</td></tr>
      </table>

      <hr>
      <h3>Tu Balance</h3>
      <p v-if="!isConnected">Conecta tu wallet.</p>
      <div v-else>
        <p>Balance: <strong>{{ balance.toString() }}</strong> {{ tokenSymbol }}</p>
        <button @click="refreshBalance" :disabled="loading">Actualizar balance</button>
      </div>

      <hr>
      <h3>Comprar Tokens</h3>
      <p>Compra 0.1 ETH en tokens ({{ (tokensPerEth / 10n).toString() }} {{ tokenSymbol }}).</p>
      <button v-if="isConnected" @click="buyTokens" :disabled="loading">
        {{ loading ? 'Procesando...' : 'Comprar 0.1 ETH' }}
      </button>

      <hr>
      <h3>Redimir Tokens</h3>
      <p>Redime todo tu saldo de vuelta a ETH.</p>
      <button v-if="isConnected && balance > 0n" @click="redeemTokens" :disabled="loading">
        {{ loading ? 'Procesando...' : 'Redimir todo' }}
      </button>
      <p v-if="balance <= 0n && isConnected">No tienes tokens para redimir.</p>

      <p v-if="msg" class="feedback">{{ msg }}</p>
    </div>
  </div>
</template>

<style scoped>
.info-table td {
  padding: 4px 12px 4px 0;
  vertical-align: top;
}
.feedback {
  margin-top: 12px;
  font-weight: bold;
}
</style>
