<script setup>
import { ref } from 'vue'
import { useWallet } from './composables/useWallet.js'
import PublicView from './components/PublicView.vue'
import CreatorPanel from './components/CreatorPanel.vue'
import AdminPanel from './components/AdminPanel.vue'

// Declarar vista activa y estado de wallet
const { account, isConnected, isCorrectNetwork, walletError, connectWallet, disconnectWallet } = useWallet()
const currentView = ref('public')
</script>

<template>
  <div>
    <h1>Sistema CFP</h1>
    <div class="nav-bar">
      <button :class="{ 'nav-active': currentView === 'public' }" @click="currentView = 'public'">Inicio</button>
      <button :class="{ 'nav-active': currentView === 'creator' }" @click="currentView = 'creator'">Creador</button>
      <button :class="{ 'nav-active': currentView === 'admin' }" @click="currentView = 'admin'">Admin</button>
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
  </div>
</template>
