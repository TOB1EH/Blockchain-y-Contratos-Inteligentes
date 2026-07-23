import { ref, shallowRef } from 'vue'
import { BrowserProvider } from 'ethers'

// Declarar estado reactivo de la wallet.
const account = ref(null) // Cuenta conectada
const chainId = ref(null) // ID de la red conectada
const signer = shallowRef(null) // Signer para firmar transacciones
const isConnected = ref(false) // Indica si la wallet está conectada
const isCorrectNetwork = ref(false) // Indica si la red conectada es la correcta
const walletError = ref(null) // Error de la wallet

// Variable para evitar configurar múltiples listeners
let listenersSetup = false

/**
 * Composable para manejar la conexión a MetaMask, estado de la wallet y eventos relacionados
 * @returns {Object} - Estado y funciones para manejar la wallet
 */
export function useWallet() {
  // Conectar wallet MetaMask y obtener provider, cuentas y red
  async function connectWallet() {
    if (!window.ethereum) {
      walletError.value = 'MetaMask no instalado'
      return
    }
    try {
      const provider = new BrowserProvider(window.ethereum)
      const accounts = await provider.send('eth_requestAccounts', [])
      account.value = accounts[0]
      signer.value = await provider.getSigner()
      isConnected.value = true
      const network = await provider.getNetwork()
      chainId.value = network.chainId
      isCorrectNetwork.value = network.chainId === 31337n
      walletError.value = null
      setupListeners()
    } catch (e) {
      walletError.value = e.message
    }
  }

  // Desconectar wallet y limpiar estado
  function disconnectWallet() {
    account.value = null
    signer.value = null
    isConnected.value = false
    chainId.value = null
    isCorrectNetwork.value = false
    walletError.value = null
  }

  // Escuchar cambios de cuenta y red en MetaMask
  function setupListeners() {
    if (listenersSetup || !window.ethereum) return
    window.ethereum.on('accountsChanged', (accounts) => {
      if (accounts.length === 0) {
        disconnectWallet()
      } else {
        account.value = accounts[0]
        connectWallet()
      }
    })
    window.ethereum.on('chainChanged', () => connectWallet())
    listenersSetup = true
  }

  return { account, chainId, signer, isConnected, isCorrectNetwork, walletError, connectWallet, disconnectWallet }
}
