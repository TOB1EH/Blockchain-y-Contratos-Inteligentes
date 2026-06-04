<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '../composables/useApi.js'

// Declarar estado reactivo: lista de creadores y carga
const api = useApi()
const creators = ref([])
const loading = ref(true)

// Obtener creadores desde el API al montar el componente
onMounted(async () => {
  const res = await api.getCreators()
  creators.value = res.data.creators || []
  loading.value = false
})
</script>

<template>
  <div>
    <h2>Creadores registrados</h2>
    <div v-if="loading">Cargando...</div>
    <table v-else-if="creators.length">
      <thead>
        <tr><th>Dirección</th><th>Nombre</th><th>Estado</th></tr>
      </thead>
      <tbody>
        <tr v-for="c in creators" :key="c.address">
          <td>{{ c.address }}</td>
          <td>{{ c.name }}</td>
          <td>{{ c.status }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else>No hay creadores registrados.</p>
  </div>
</template>
