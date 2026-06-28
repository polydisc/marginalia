import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from './api'

/** Build a Response-like stub for the global fetch mock. */
function reply(body: unknown, init: { status?: number; text?: string } = {}) {
  const status = init.status ?? 200
  const text = init.text ?? (body === undefined ? '' : JSON.stringify(body))
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 503 ? 'Service Unavailable' : 'OK',
    text: async () => text,
  } as Response
}

function mockFetch(response: Response) {
  const spy = vi.fn((_path: string, _init?: RequestInit) => Promise.resolve(response))
  vi.stubGlobal('fetch', spy)
  return spy
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api request layer', () => {
  it('GETs a relative path and returns the parsed JSON body', async () => {
    const fetchSpy = mockFetch(reply([{ id: 1, title: 'Dubliners' }]))
    const catalog = await api.getCatalog()

    expect(catalog).toEqual([{ id: 1, title: 'Dubliners' }])
    const [path, init] = fetchSpy.mock.calls[0]
    expect(path).toBe('/catalog')
    expect((init as RequestInit).headers).toMatchObject({
      'Content-Type': 'application/json',
    })
  })

  it('POSTs a JSON body for create endpoints', async () => {
    const fetchSpy = mockFetch(reply({ id: 7, title: 'Ulysses', author: 'Joyce' }))
    await api.createWork('Ulysses', 'Joyce')

    const [path, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(path).toBe('/works')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ title: 'Ulysses', author: 'Joyce' })
  })

  it('URL-encodes path parameters such as barcodes', async () => {
    const fetchSpy = mockFetch(reply({ barcode: 'B 1/2', availability: 'available' }))
    await api.getItem('B 1/2')

    expect(fetchSpy.mock.calls[0][0]).toBe('/items/B%201%2F2')
  })

  it('normalises empty optional fields to null in the payload', async () => {
    const fetchSpy = mockFetch(reply({ id: 3 }))
    await api.catalogManifestation(1, 'Ed.', 'book', '', '')

    const init = fetchSpy.mock.calls[0][1] as RequestInit
    expect(JSON.parse(init.body as string)).toMatchObject({ isbn: null, publisher: null })
  })

  it('throws ApiError carrying status, detail and domain code on a 4xx', async () => {
    mockFetch(
      reply(
        { detail: 'item B001 is already on loan', error: 'ItemNotAvailable' },
        { status: 409 },
      ),
    )

    await expect(api.checkOut('B001', 'C001')).rejects.toMatchObject({
      status: 409,
      message: 'item B001 is already on loan',
      code: 'ItemNotAvailable',
    })
    await expect(api.checkOut('B001', 'C001')).rejects.toBeInstanceOf(ApiError)
  })

  it('falls back to statusText / "Error" when the error body is not JSON', async () => {
    mockFetch(reply(undefined, { status: 503, text: '<html>proxy down</html>' }))

    await expect(api.getCatalog()).rejects.toMatchObject({
      status: 503,
      message: 'Service Unavailable',
      code: 'Error',
    })
  })

  it('returns null for an empty 2xx body without throwing', async () => {
    mockFetch(reply(undefined, { status: 200, text: '' }))
    await expect(api.expireHolds()).resolves.toBeNull()
  })
})

describe('api endpoint map', () => {
  // One assertion per endpoint: the path, method and (where relevant) the JSON
  // body it sends. Guards every call site against an accidental path/verb drift.
  type Call = { method: string; path: string; body?: unknown }

  const call = async (run: () => Promise<unknown>): Promise<Call> => {
    const fetchSpy = mockFetch(reply({}))
    await run()
    const [path, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    return {
      method: (init.method ?? 'GET').toUpperCase(),
      path,
      body: init.body ? JSON.parse(init.body as string) : undefined,
    }
  }

  it.each<[string, () => Promise<unknown>, Call]>([
    ['createWork', () => api.createWork('U', 'J'), { method: 'POST', path: '/works', body: { title: 'U', author: 'J' } }],
    ['addItem', () => api.addItem(3, 'B1'), { method: 'POST', path: '/manifestations/3/items', body: { barcode: 'B1' } }],
    ['getCatalog', () => api.getCatalog(), { method: 'GET', path: '/catalog' }],
    ['changeItemState', () => api.changeItemState('B1', 'lost'), { method: 'POST', path: '/items/B1/state', body: { state: 'lost' } }],
    ['updateWork', () => api.updateWork(2, 'T', 'A'), { method: 'PUT', path: '/works/2', body: { title: 'T', author: 'A' } }],
    ['registerPatron', () => api.registerPatron('C1', 'student'), { method: 'POST', path: '/patrons', body: { card_number: 'C1', category: 'student', expires_on: null } }],
    ['suspendPatron', () => api.suspendPatron('C1'), { method: 'POST', path: '/patrons/C1/suspend' }],
    ['reinstatePatron', () => api.reinstatePatron('C1'), { method: 'POST', path: '/patrons/C1/reinstate' }],
    ['updatePatron', () => api.updatePatron('C1', 'child', '2027-01-01'), { method: 'PUT', path: '/patrons/C1', body: { category: 'child', expires_on: '2027-01-01' } }],
    ['getPatron', () => api.getPatron('C1'), { method: 'GET', path: '/patrons/C1' }],
    ['patronLoans', () => api.patronLoans('C1'), { method: 'GET', path: '/patrons/C1/loans' }],
    ['patronHolds', () => api.patronHolds('C1'), { method: 'GET', path: '/patrons/C1/holds' }],
    ['checkOut', () => api.checkOut('B1', 'C1'), { method: 'POST', path: '/loans', body: { item_barcode: 'B1', patron_card: 'C1' } }],
    ['checkIn', () => api.checkIn('B1'), { method: 'POST', path: '/loans/B1/return' }],
    ['renew', () => api.renew('B1'), { method: 'POST', path: '/loans/B1/renew' }],
    ['placeHold', () => api.placeHold(5, 'C1'), { method: 'POST', path: '/holds', body: { manifestation_id: 5, patron_card: 'C1' } }],
    ['readyHolds', () => api.readyHolds(), { method: 'GET', path: '/holds/ready' }],
    ['expireHolds', () => api.expireHolds(), { method: 'POST', path: '/holds/expire' }],
    ['cancelHold', () => api.cancelHold(9), { method: 'POST', path: '/holds/9/cancel' }],
    ['getItem', () => api.getItem('B1'), { method: 'GET', path: '/items/B1' }],
  ])('%s targets the right endpoint', async (_name, run, expected) => {
    expect(await call(run)).toEqual(expected)
  })

  it('updateManifestation PUTs the bibliographic fields', async () => {
    expect(await call(() => api.updateManifestation(4, 'T', 'book', '978', 'Pub'))).toEqual({
      method: 'PUT',
      path: '/manifestations/4',
      body: { title: 'T', material_type: 'book', isbn: '978', publisher: 'Pub' },
    })
  })

  it('catalogManifestation keeps a provided isbn/publisher', async () => {
    expect(await call(() => api.catalogManifestation(1, 'T', 'book', '978', 'Pub'))).toEqual({
      method: 'POST',
      path: '/manifestations',
      body: { work_id: 1, title: 'T', material_type: 'book', isbn: '978', publisher: 'Pub' },
    })
  })
})
