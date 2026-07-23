<script setup>
import { ref, provide } from 'vue'
import { useWallet } from './composables/useWallet.js'
import PublicView from './components/PublicView.vue'
import CreatorPanel from './components/CreatorPanel.vue'
import AdminPanel from './components/AdminPanel.vue'
import TokenPanel from './components/TokenPanel.vue'
import EnsPanel from './components/EnsPanel.vue'
import GuaranteePanel from './components/GuaranteePanel.vue'

const { account, isConnected, isCorrectNetwork, walletError, connectWallet, disconnectWallet } = useWallet()
const currentView = ref('public')
provide('navigateTo', (view) => { currentView.value = view })
</script>

<template>
  <div>
    <h1>Sistema CFP</h1>
    <div class="nav-bar">
      <button :class="{ 'nav-active': currentView === 'public' }" @click="currentView = 'public'">Inicio</button>
      <button :class="{ 'nav-active': currentView === 'creator' }" @click="currentView = 'creator'">Creador</button>
      <button :class="{ 'nav-active': currentView === 'admin' }" @click="currentView = 'admin'">Admin</button>
      <button :class="{ 'nav-active': currentView === 'token' }" @click="currentView = 'token'">Token</button>
      <button :class="{ 'nav-active': currentView === 'ens' }" @click="currentView = 'ens'">ENS</button>
      <button :class="{ 'nav-active': currentView === 'guarantee' }" @click="currentView = 'guarantee'">Garantia</button>
      <span class="nav-wallet">
        <span v-if="!isConnected">
          <button @click="connectWallet">Conectar MetaMask</button>
        </span>
        <span v-else>
          <span class="wallet-address">{{ account }}</span>
          <span v-if="!isCorrectNetwork" class="network-error">Red incorrecta (debe ser 31337)</span>
          <button @click="disconnectWallet">Desconectar</button>
        </span>
      </span>
    </div>
    <div v-if="walletError" class="wallet-error">{{ walletError }}</div>
    <hr>
    <PublicView v-if="currentView === 'public'" />
    <CreatorPanel v-else-if="currentView === 'creator'" />
    <AdminPanel v-else-if="currentView === 'admin'" />
    <TokenPanel v-else-if="currentView === 'token'" />
    <EnsPanel v-else-if="currentView === 'ens'" />
    <GuaranteePanel v-else-if="currentView === 'guarantee'" />
  </div>
</template>
