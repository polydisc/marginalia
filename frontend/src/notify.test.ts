import { describe, expect, it, vi } from 'vitest'
import { ApiError } from './api'
import { runApi } from './notify'

describe('runApi', () => {
  it('wraps a successful call as { ok: true } with its text', async () => {
    const res = await runApi(async () => 'Hold placed — you are #2 in the queue.')
    expect(res).toEqual({ ok: true, text: 'Hold placed — you are #2 in the queue.' })
  })

  it('surfaces an ApiError detail message alone (no status/code prefix)', async () => {
    const res = await runApi(async () => {
      throw new ApiError(409, 'item B001 is already on loan', 'ItemNotAvailable')
    })
    expect(res).toEqual({ ok: false, text: 'item B001 is already on loan' })
  })

  it('maps an unexpected/network error to a calm patron message', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const res = await runApi(async () => {
      throw new TypeError('Failed to fetch')
    })
    expect(res).toEqual({ ok: false, text: 'Something went wrong — please try again.' })
    // The real error is logged for the developer console, not shown to the patron.
    expect(spy).toHaveBeenCalledOnce()
  })
})
