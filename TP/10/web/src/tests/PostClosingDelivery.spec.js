import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import PostClosingDelivery from '../components/PostClosingDelivery.vue'

const mockPostDeliver = vi.fn()

vi.mock('../composables/useApi.js', () => ({
  useApi: () => ({
    postDeliver: mockPostDeliver
  })
}))

function createMockFile(name, content, type) {
  const blob = new Blob([content], { type })
  return new File([blob], name, { type })
}

function createReceiptFile(proposalId) {
  const receipt = JSON.stringify({
    proposalId,
    callId: '0xcall123',
    proof: { '0xleaf': [] }
  })
  return createMockFile('recibo.json', receipt, 'application/json')
}

describe('PostClosingDelivery.vue', () => {
  beforeEach(() => {
    mockPostDeliver.mockReset()
  })

  it('renderiza el formulario de entrega', () => {
    const wrapper = mount(PostClosingDelivery)
    expect(wrapper.find('h3').text()).toContain('Entrega Definitiva')
    expect(wrapper.find('button').text()).toContain('Entregar Archivos Definitivos')
  })

  it('muestra error si faltan recibo o archivos', async () => {
    const wrapper = mount(PostClosingDelivery)
    await wrapper.find('button').trigger('click')
    expect(wrapper.find('.feedback').text()).toContain('Debes subir tu recibo')
  })

  it('deshabilita el botón si no hay recibo o archivos', () => {
    const wrapper = mount(PostClosingDelivery)
    const btn = wrapper.find('button')
    expect(btn.element.disabled).toBe(true)
  })

  it('llama a la API y muestra éxito en entrega válida', async () => {
    mockPostDeliver.mockResolvedValue({
      status: 201,
      data: {
        message: 'OK',
        filesRoot: '0xroot',
        proposalId: '0xproposal'
      }
    })

    const wrapper = mount(PostClosingDelivery)

    // Subir recibo
    const receiptInput = wrapper.findAll('input[type="file"]')[0]
    const receiptFile = createReceiptFile('0xproposal')
    Object.defineProperty(receiptInput.element, 'files', {
      value: [receiptFile],
      writable: false
    })
    await receiptInput.trigger('change')

    // Subir archivos físicos
    const filesInput = wrapper.findAll('input[type="file"]')[1]
    const pdfFile = createMockFile('doc.pdf', 'PDF content', 'application/pdf')
    Object.defineProperty(filesInput.element, 'files', {
      value: [pdfFile],
      writable: false
    })
    await filesInput.trigger('change')

    // Enviar
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(mockPostDeliver).toHaveBeenCalled()
    expect(wrapper.text()).toContain('¡Archivos entregados')
  })

  it('muestra error si la API rechaza la entrega', async () => {
    mockPostDeliver.mockResolvedValue({
      status: 403,
      data: { message: 'CALL_NOT_CLOSED' }
    })

    const wrapper = mount(PostClosingDelivery)

    const receiptInput = wrapper.findAll('input[type="file"]')[0]
    const receiptFile = createReceiptFile('0xproposal')
    Object.defineProperty(receiptInput.element, 'files', {
      value: [receiptFile],
      writable: false
    })
    await receiptInput.trigger('change')

    const filesInput = wrapper.findAll('input[type="file"]')[1]
    const pdfFile = createMockFile('doc.pdf', 'content', 'application/pdf')
    Object.defineProperty(filesInput.element, 'files', {
      value: [pdfFile],
      writable: false
    })
    await filesInput.trigger('change')

    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('CALL_NOT_CLOSED')
  })
})
