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
    <h1>TP10 - Sistema CFP</h1>
    <div>
      <button @click="currentView = 'public'">Inicio</button>
      <button @click="currentView = 'creator'">Creador</button>
      <button @click="currentView = 'admin'">Admin</button>
      <span v-if="!isConnected">
        <button @click="connectWallet">Conectar MetaMask</button>
      </span>
      <span v-else>
        <span>{{ account }}</span>
        <span v-if="!isCorrectNetwork" style="color:red"> Red incorrecta (debe ser 31337)</span>
        <button @click="disconnectWallet">Desconectar</button>
      </span>
    </div>
    <div v-if="walletError" style="color:red">{{ walletError }}</div>
    <hr>
    <PublicView v-if="currentView === 'public'" />
    <CreatorPanel v-else-if="currentView === 'creator'" />
    <AdminPanel v-else-if="currentView === 'admin'" />
  </div>
</template>
