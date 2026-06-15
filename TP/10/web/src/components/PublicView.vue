<script setup>
import { ref, onMounted, computed } from 'vue'
import { useApi } from '../composables/useApi.js'

// Declarar estado reactivo: lista de creadores y llamados
const api = useApi()
const creators = ref([])
const calls = ref([])
const loadingCreators = ref(true)
const loadingCalls = ref(true)
const filterCreator = ref('')

// Obtener creadores y llamados desde el API al montar el componente
onMounted(async () => {
  const [cr, cl] = await Promise.all([
    api.getCreators(),
    api.getCalls()
  ])
  creators.value = cr.data.creators || []
  calls.value = cl.data.calls || []
  loadingCreators.value = false
  loadingCalls.value = false
})

// Llamados filtrados por creador seleccionado
const filteredCalls = computed(() => {
  if (!filterCreator.value) return calls.value
  return calls.value.filter(c => c.creator && c.creator.toLowerCase() === filterCreator.value.toLowerCase())
})

// Seleccionar un creador para filtrar sus llamados
function selectCreator(creatorAddress) {
  filterCreator.value = creatorAddress === filterCreator.value ? '' : creatorAddress
}
</script>

<template>
  <div>
    <h2>Creadores registrados</h2>
    <div v-if="loadingCreators">Cargando...</div>
    <table v-else-if="creators.length">
      <thead>
        <tr>
          <th>Dirección</th>
          <th>Nombre</th>
          <th>Estado</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in creators" :key="c.address" :class="{ selected: filterCreator === c.address }">
          <td>{{ c.address }}</td>
          <td>{{ c.name }}</td>
          <td>{{ c.status }}</td>
          <td><button @click="selectCreator(c.address)">Ver llamados</button></td>
        </tr>
      </tbody>
    </table>
    <p v-else>No hay creadores registrados.</p>

    <h2 v-if="filterCreator">Llamados de {{ filterCreator }}</h2>
    <h2 v-else>Llamados abiertos</h2>
    <div v-if="loadingCalls">Cargando llamados...</div>
    <table v-else-if="filteredCalls.length">
      <thead>
        <tr>
          <th>Título</th>
          <th>Descripción</th>
          <th>Creador</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="cl in filteredCalls" :key="cl.call_id">
          <td>{{ cl.title }}</td>
          <td>{{ cl.description }}</td>
          <td>{{ cl.creator }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else>No hay llamados disponibles.</p>
  </div>
</template>

<style scoped>
.selected {
  background-color: #e3f2fd;
}
</style>
