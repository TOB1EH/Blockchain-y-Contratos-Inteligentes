import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import PublicView from '../components/PublicView.vue'

vi.mock('../composables/useApi.js', () => ({
  useApi: () => ({
    getCreators: vi.fn().mockResolvedValue({
      status: 200,
      data: { creators: [] }
    }),
    getCalls: vi.fn().mockResolvedValue({
      status: 200,
      data: { calls: [] }
    }),
    getCallDeliveries: vi.fn().mockResolvedValue({
      status: 200,
      data: { deliveries: [] }
    }),
  })
}))

describe('PublicView.vue', () => {
  it('renderiza el estado inicial mientras carga', async () => {
    const wrapper = mount(PublicView)
    expect(wrapper.text()).toContain('Cargando...')
  })
})