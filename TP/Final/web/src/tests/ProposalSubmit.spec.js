import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ProposalSubmit from '../components/ProposalSubmit.vue'

const MOCK_CALL_ID = '0xabc123'

// Mock ethers keccak256
vi.mock('ethers', () => ({
  keccak256: vi.fn(() => '0xmockedhash1234567890abcdef1234567890abcdef1234567890abcdef12345678')
}))

// Mock useApi
const mockPostRegisterProposal = vi.fn()
vi.mock('../composables/useApi.js', () => ({
  useApi: () => ({
    postRegisterProposal: mockPostRegisterProposal
  })
}))

function createMockFile(name, content, type) {
  const blob = new Blob([content], { type })
  return new File([blob], name, { type })
}

describe('ProposalSubmit.vue', () => {
  beforeEach(() => {
    mockPostRegisterProposal.mockReset()
  })

  it('renderiza el formulario de propuesta', () => {
    const wrapper = mount(ProposalSubmit, {
      props: { callId: MOCK_CALL_ID }
    })
    expect(wrapper.find('h3').text()).toContain('Presentar Propuesta')
    expect(wrapper.find('input[type="file"]').exists()).toBe(true)
    expect(wrapper.find('button').text()).toContain('Obtener Recibo')
  })

  it('muestra error si faltan campos al enviar', async () => {
    const wrapper = mount(ProposalSubmit, {
      props: { callId: MOCK_CALL_ID }
    })
    await wrapper.find('button').trigger('click')
    expect(wrapper.find('.feedback').text()).toContain('Debes completar título')
  })

  it('llama a la API y muestra éxito al enviar propuesta válida', async () => {
    mockPostRegisterProposal.mockResolvedValue({
      status: 201,
      data: {
        proposalId: '0xproposal123',
        proof: { callId: [] }
      }
    })

    const wrapper = mount(ProposalSubmit, {
      props: { callId: MOCK_CALL_ID }
    })

    // Llenar campos
    await wrapper.find('input').setValue('Mi propuesta')
    await wrapper.findAll('textarea')[0].setValue('Descripción secreta')

    // Simular subida de archivo
    const fileInput = wrapper.find('input[type="file"]')
    const mockFile = createMockFile('doc.pdf', 'contenido', 'application/pdf')
    Object.defineProperty(fileInput.element, 'files', {
      value: [mockFile],
      writable: false
    })
    await fileInput.trigger('change')

    // Enviar
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(mockPostRegisterProposal).toHaveBeenCalledWith(
      MOCK_CALL_ID,
      'Mi propuesta',
      'Descripción secreta',
      expect.any(Array)
    )
    expect(wrapper.text()).toContain('¡Propuesta registrada con éxito!')
  })

  it('muestra error si la API rechaza la propuesta', async () => {
    mockPostRegisterProposal.mockResolvedValue({
      status: 400,
      data: { message: 'INVALID_TITLE' }
    })

    const wrapper = mount(ProposalSubmit, {
      props: { callId: MOCK_CALL_ID }
    })

    await wrapper.find('input').setValue('Título')
    await wrapper.findAll('textarea')[0].setValue('Descripción')

    const fileInput = wrapper.find('input[type="file"]')
    const mockFile = createMockFile('doc.pdf', 'data', 'application/pdf')
    Object.defineProperty(fileInput.element, 'files', {
      value: [mockFile],
      writable: false
    })
    await fileInput.trigger('change')

    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('INVALID_TITLE')
  })
})
