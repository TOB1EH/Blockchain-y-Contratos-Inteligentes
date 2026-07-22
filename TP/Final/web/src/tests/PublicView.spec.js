import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import PublicView from '../components/PublicView.vue'
// import * as useApiModule from '../composables/useApi.js'

// Hacer un mock falso de la API para no depender del servidor real
vi.mock('../composables/useApi.js', () => ({
  useApi: () => ({
    getCreators: vi.fn().mockResolvedValue({
      status: 200,
      data: { creators: [] }
    })
  })
}))

describe('PublicView.vue', () => {
  it('renderiza el mensaje correcto cuando la lista de creadores está vacía', async () => {
    const wrapper = mount(PublicView)

    // Esperar a que se resuelva la promesa del onMounted
    await new Promise(r => setTimeout(r, 10))

    expect(wrapper.text()).toContain('No hay creadores registrados.')
    expect(wrapper.text()).not.toContain('Cargando...')
  })
})