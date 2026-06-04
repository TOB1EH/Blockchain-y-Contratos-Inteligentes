// Construir dominio EIP-712 con chainId y direccion del contrato
export function getDomain(chainId, contractAddress) {
  return {
    name: 'CFP API',
    version: '1',
    chainId: BigInt(chainId),
    verifyingContract: contractAddress,
  }
}

// Definir tipos EIP-712 para RegisterRequest y AdminActionRequest
export const TYPES = {
  RegisterRequest: [
    { name: 'operation', type: 'string' },
    { name: 'contract', type: 'address' },
    { name: 'nonce', type: 'uint256' },
    { name: 'name', type: 'string' },
  ],
  AdminActionRequest: [
    { name: 'operation', type: 'string' },
    { name: 'contract', type: 'address' },
    { name: 'nonce', type: 'uint256' },
    { name: 'target', type: 'address' },
  ],
}

// Construir mensaje EIP-712 para registro off-chain
export function buildRegisterMessage(chainId, contractAddress, name) {
  return {
    domain: getDomain(chainId, contractAddress),
    types: { RegisterRequest: TYPES.RegisterRequest },
    message: { operation: 'register', contract: contractAddress, nonce: 0n, name },
  }
}

// Construir mensaje EIP-712 para actualizar perfil
export function buildUpdateMessage(chainId, contractAddress, nonce, name) {
  return {
    domain: getDomain(chainId, contractAddress),
    types: { RegisterRequest: TYPES.RegisterRequest },
    message: { operation: 'update', contract: contractAddress, nonce: BigInt(nonce), name },
  }
}

// Construir mensaje EIP-712 para autorizar creador
export function buildAuthorizeMessage(chainId, contractAddress, nonce, target) {
  return {
    domain: getDomain(chainId, contractAddress),
    types: { AdminActionRequest: TYPES.AdminActionRequest },
    message: { operation: 'authorize', contract: contractAddress, nonce: BigInt(nonce), target },
  }
}

// Construir mensaje EIP-712 para desautorizar creador
export function buildUnauthorizeMessage(chainId, contractAddress, nonce, target) {
  return {
    domain: getDomain(chainId, contractAddress),
    types: { AdminActionRequest: TYPES.AdminActionRequest },
    message: { operation: 'unauthorize', contract: contractAddress, nonce: BigInt(nonce), target },
  }
}
