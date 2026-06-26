export type MaterialType = 'book' | 'reference' | 'audiovisual'
export type PatronCategory = 'general' | 'student' | 'child'
export type Availability =
  | 'available'
  | 'on_loan'
  | 'on_hold_shelf'
  | 'in_repair'
  | 'lost'
  | 'withdrawn'

export interface Work {
  id: number
  title: string
  author: string
}

export interface Manifestation {
  id: number
  work_id: number
  title: string
  material_type: string
  isbn: string | null
  publisher: string | null
}

export interface Item {
  id: number
  manifestation_id: number
  barcode: string
  state: string
}

export interface Patron {
  id: number
  card_number: string
  category: string
  status: string
  expires_on: string | null
}

export interface Loan {
  loan_id: number
  item_barcode: string
  patron_card: string
  due_date: string
  renewal_count: number
}

export interface CheckIn {
  item_barcode: string
  hold_triggered: boolean
  ready_hold_id: number | null
}

export interface Hold {
  hold_id: number
  manifestation_id: number
  patron_card: string
  queue_position: number
  status: string
}

export interface ItemAvailability {
  barcode: string
  intrinsic_state: string
  availability: Availability
}

export interface ExpireHolds {
  expired: number
  reassigned: number
}

// --- read models ------------------------------------------------------------

export interface CatalogItem {
  barcode: string
  availability: Availability
}

export interface CatalogManifestation {
  id: number
  title: string
  material_type: string
  isbn: string | null
  publisher: string | null
  items: CatalogItem[]
}

export interface CatalogWork {
  id: number
  title: string
  author: string
  manifestations: CatalogManifestation[]
}

export interface LoanLine {
  item_barcode: string
  title: string
  author: string
  due_date: string
  renewal_count: number
  overdue: boolean
}

export interface ReadyHold {
  hold_id: number
  title: string
  patron_card: string
  item_barcode: string | null
  queue_position: number
}

export interface PatronHold {
  hold_id: number
  manifestation_id: number
  title: string
  status: string
  queue_position: number
  pickup_by: string | null
}

export interface CancelHold {
  hold_id: number
  status: string
  reassigned: number
}
