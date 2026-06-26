import type {
  CancelHold,
  CatalogWork,
  CheckIn,
  ExpireHolds,
  Hold,
  Item,
  ItemAvailability,
  Loan,
  LoanLine,
  Manifestation,
  MaterialType,
  Patron,
  PatronCategory,
  PatronHold,
  ReadyHold,
  Work,
} from './types'

/** Raised when the backend returns a non-2xx; carries the domain error name. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  constructor(status: number, detail: string, code: string) {
    super(detail)
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  const text = await res.text()
  // Tolerate a non-JSON body (proxy 503, an unexpected HTML 500): fall back to
  // the status text rather than throwing a cryptic SyntaxError.
  let body: any = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = null
  }
  if (!res.ok) {
    const detail = body?.detail ?? res.statusText
    const code = body?.error ?? 'Error'
    throw new ApiError(res.status, detail, code)
  }
  return body as T
}

const post = <T>(path: string, json?: unknown) =>
  request<T>(path, { method: 'POST', body: json ? JSON.stringify(json) : undefined })

const put = <T>(path: string, json: unknown) =>
  request<T>(path, { method: 'PUT', body: JSON.stringify(json) })

export const api = {
  // --- catalog ---
  createWork: (title: string, author: string) =>
    post<Work>('/works', { title, author }),

  catalogManifestation: (
    work_id: number,
    title: string,
    material_type: MaterialType,
    isbn?: string,
    publisher?: string,
  ) =>
    post<Manifestation>('/manifestations', {
      work_id,
      title,
      material_type,
      isbn: isbn || null,
      publisher: publisher || null,
    }),

  addItem: (manifestation_id: number, barcode: string) =>
    post<Item>(`/manifestations/${manifestation_id}/items`, { barcode }),

  getCatalog: () => request<CatalogWork[]>('/catalog'),

  changeItemState: (barcode: string, state: string) =>
    post<Item>(`/items/${encodeURIComponent(barcode)}/state`, { state }),

  updateWork: (id: number, title: string, author: string) =>
    put<Work>(`/works/${id}`, { title, author }),

  updateManifestation: (
    id: number,
    title: string,
    material_type: MaterialType,
    isbn?: string,
    publisher?: string,
  ) =>
    put<Manifestation>(`/manifestations/${id}`, {
      title,
      material_type,
      isbn: isbn || null,
      publisher: publisher || null,
    }),

  // --- patrons ---
  registerPatron: (
    card_number: string,
    category: PatronCategory,
    expires_on?: string,
  ) =>
    post<Patron>('/patrons', {
      card_number,
      category,
      expires_on: expires_on || null,
    }),

  suspendPatron: (card: string) =>
    post<Patron>(`/patrons/${encodeURIComponent(card)}/suspend`),

  reinstatePatron: (card: string) =>
    post<Patron>(`/patrons/${encodeURIComponent(card)}/reinstate`),

  updatePatron: (
    card: string,
    category: PatronCategory,
    expires_on?: string,
  ) =>
    put<Patron>(`/patrons/${encodeURIComponent(card)}`, {
      category,
      expires_on: expires_on || null,
    }),

  getPatron: (card: string) =>
    request<Patron>(`/patrons/${encodeURIComponent(card)}`),

  patronLoans: (card: string) =>
    request<LoanLine[]>(`/patrons/${encodeURIComponent(card)}/loans`),

  patronHolds: (card: string) =>
    request<PatronHold[]>(`/patrons/${encodeURIComponent(card)}/holds`),

  // --- circulation ---
  checkOut: (item_barcode: string, patron_card: string) =>
    post<Loan>('/loans', { item_barcode, patron_card }),

  checkIn: (item_barcode: string) =>
    post<CheckIn>(`/loans/${encodeURIComponent(item_barcode)}/return`),

  renew: (item_barcode: string) =>
    post<Loan>(`/loans/${encodeURIComponent(item_barcode)}/renew`),

  placeHold: (manifestation_id: number, patron_card: string) =>
    post<Hold>('/holds', { manifestation_id, patron_card }),

  readyHolds: () => request<ReadyHold[]>('/holds/ready'),

  expireHolds: () => post<ExpireHolds>('/holds/expire'),

  cancelHold: (holdId: number) =>
    post<CancelHold>(`/holds/${holdId}/cancel`),

  getItem: (barcode: string) =>
    request<ItemAvailability>(`/items/${encodeURIComponent(barcode)}`),
}
