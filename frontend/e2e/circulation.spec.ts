import { test, expect, type Page } from '@playwright/test'

// Unique ids per test so specs stay independent against the shared SQLite file.
let counter = 0
function uid(): string {
  counter += 1
  return `${Date.now().toString().slice(-6)}${counter}`
}

const log = (page: Page) => page.getByTestId('activity-log')

async function gotoCatalog(page: Page) {
  await page.getByTestId('nav-catalog').click()
  await expect(page.getByTestId('cat-submit')).toBeVisible()
}
async function gotoDesk(page: Page) {
  await page.getByTestId('nav-desk').click()
  await expect(page.getByTestId('desk-go')).toBeVisible()
}

/** Catalog a book on the Catalog screen; returns its manifestation id. */
async function catalogBook(
  page: Page,
  opts: { barcode: string; material?: 'book' | 'reference' | 'audiovisual' },
): Promise<number> {
  await gotoCatalog(page)
  await page.getByTestId('cat-title').fill(`Title ${opts.barcode}`)
  await page.getByTestId('cat-author').fill('Author')
  await page.getByTestId('cat-material').selectOption(opts.material ?? 'book')
  await page.getByTestId('cat-isbn').fill('')
  await page.getByTestId('cat-barcode').fill(opts.barcode)
  await page.getByTestId('cat-submit').click()
  await expect(page.getByTestId('cat-msg')).toContainText(`item ${opts.barcode} (available)`)
  const text = (await page.getByTestId('cat-msg').textContent()) ?? ''
  const m = text.match(/manifestation #(\d+)/)
  expect(m, 'manifestation id should appear in the catalog message').not.toBeNull()
  return Number(m![1])
}

async function registerPatron(page: Page, card: string) {
  await gotoDesk(page)
  await page.getByTestId('reg-card').fill(card)
  await page.getByTestId('reg-category').selectOption('general')
  await page.getByTestId('reg-submit').click()
  await expect(log(page)).toContainText(`Registered patron ${card}`)
}

async function scan(page: Page, mode: 'out' | 'in' | 'renew', card: string, barcode: string) {
  await page.getByTestId(`mode-${mode}`).click()
  await page.getByTestId('desk-card').fill(card)
  await page.getByTestId('desk-barcode').fill(barcode)
  await page.getByTestId('desk-go').click()
}

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Circulation Desk' })).toBeVisible()
})

test('check out from the desk, see the loan, block a double checkout, renew, return', async ({
  page,
}) => {
  const barcode = `B${uid()}`
  const card = `C${uid()}`
  await catalogBook(page, { barcode })
  await registerPatron(page, card)

  await scan(page, 'out', card, barcode)
  await expect(log(page)).toContainText(`Checked out ${barcode} to ${card}`)
  await expect(page.getByTestId('session-who')).toHaveText(card)
  await expect(page.getByTestId(`loan-${barcode}`)).toContainText('on loan')

  // Double checkout -> 409 surfaced in the activity log.
  await scan(page, 'out', card, barcode)
  await expect(log(page)).toContainText('409 ItemNotAvailable')

  await scan(page, 'renew', card, barcode)
  await expect(log(page)).toContainText(`Renewed ${barcode}`)

  await scan(page, 'in', card, barcode)
  await expect(log(page)).toContainText(`Returned ${barcode} — back on shelf`)
})

test('catalog tree reflects derived on_loan availability', async ({ page }) => {
  const barcode = `B${uid()}`
  const card = `C${uid()}`
  const title = `Title ${barcode}`
  await catalogBook(page, { barcode })
  await registerPatron(page, card)
  await scan(page, 'out', card, barcode)
  await expect(log(page)).toContainText(`Checked out ${barcode}`)

  // The copy now reads on_loan in the catalog tree (derived, not stored).
  await gotoCatalog(page)
  await page.getByTestId('cat-q').fill(title)
  await expect(page.locator('.work-row')).toHaveCount(1) // search narrowed to one
  await page.locator('.work-row').click()
  await expect(page.getByTestId(`copy-${barcode}`)).toContainText('on loan')
})

test('mark a copy in repair from the catalog; it becomes unloanable', async ({
  page,
}) => {
  const barcode = `B${uid()}`
  const card = `C${uid()}`
  await catalogBook(page, { barcode })
  await registerPatron(page, card)

  await gotoCatalog(page)
  await page.getByTestId('cat-q').fill(`Title ${barcode}`)
  await expect(page.locator('.work-row')).toHaveCount(1)
  await page.locator('.work-row').click()
  await page.getByTestId(`copy-state-${barcode}`).selectOption('in_repair')
  await expect(page.getByTestId(`copy-${barcode}`)).toContainText('in repair')

  await gotoDesk(page)
  await scan(page, 'out', card, barcode)
  await expect(log(page)).toContainText('409 ItemNotAvailable')
})

test('edit a manifestation and a work from the catalog', async ({ page }) => {
  const barcode = `B${uid()}`
  const mid = await catalogBook(page, { barcode })

  // Remount the catalog (via the desk) so the expand state is clean.
  await gotoDesk(page)
  await gotoCatalog(page)
  await page.getByTestId('cat-q').fill(`Title ${barcode}`)
  await expect(page.locator('.work-row')).toHaveCount(1)
  await page.locator('.work-row').click()

  await page.getByTestId(`manif-edit-${mid}`).click()
  await page.getByTestId(`manif-isbn-${mid}`).fill('978-9999999999')
  await page.getByTestId(`manif-material-${mid}`).selectOption('audiovisual')
  await page.getByTestId(`manif-save-${mid}`).click()
  await expect(page.getByTestId('works')).toContainText('978-9999999999')

  await page.locator('[data-testid^="work-edit-"]').click()
  await page.locator('[data-testid^="work-title-"]').fill(`Renamed ${barcode}`)
  await page.locator('[data-testid^="work-save-"]').click()
  await page.getByTestId('cat-q').fill('') // clear the filter
  await expect(page.getByTestId('works')).toContainText(`Renamed ${barcode}`)
})

test('edit a patron category from the desk', async ({ page }) => {
  const card = `C${uid()}`
  await registerPatron(page, card)
  await expect(page.getByTestId('session-who')).toHaveText(card)

  await page.getByTestId('session-edit').click()
  await page.getByTestId('patron-edit-category').selectOption('student')
  await page.getByTestId('patron-edit-save').click()
  await expect(log(page)).toContainText(`Updated ${card} → student`)
})

test('place a hold, see it in the patron view, and cancel it', async ({
  page,
}) => {
  const barcode = `B${uid()}`
  const card = `C${uid()}`
  const mid = await catalogBook(page, { barcode })
  await registerPatron(page, card)

  // Place a hold for this patron (Catalog screen).
  await gotoCatalog(page)
  await page.getByTestId('hold-card').fill(card)
  await page.getByTestId('cat-q').fill(`Title ${barcode}`)
  await expect(page.locator('.work-row')).toHaveCount(1)
  await page.locator('.work-row').click()
  await page.getByTestId(`hold-${mid}`).click()

  // Reload the patron on the desk and cancel the hold.
  await gotoDesk(page)
  await page.getByTestId('desk-card').fill(card)
  await page.getByTestId('desk-barcode').click() // blur loads the patron
  await expect(page.getByTestId('patron-holds')).toContainText('in queue')
  await page.getByTestId('patron-holds').getByRole('button', { name: 'Cancel' }).click()
  await expect(log(page)).toContainText('Cancelled hold')
})

test('reference material is not for loan -> 422', async ({ page }) => {
  const barcode = `R${uid()}`
  const card = `C${uid()}`
  await catalogBook(page, { material: 'reference', barcode })
  await registerPatron(page, card)
  await scan(page, 'out', card, barcode)
  await expect(log(page)).toContainText('422 NotForLoan')
})

test('place a hold, return the copy, and fulfil it from the hold shelf', async ({
  page,
}) => {
  const barcode = `B${uid()}`
  const owner = `C${uid()}`
  const waiter = `C${uid()}`
  const manifestationId = await catalogBook(page, { barcode })
  await registerPatron(page, owner)
  await registerPatron(page, waiter)

  await scan(page, 'out', owner, barcode)
  await expect(log(page)).toContainText(`Checked out ${barcode}`)

  // Waiter places a hold on the manifestation (Catalog screen).
  await gotoCatalog(page)
  await page.getByTestId('hold-card').fill(waiter)
  await page.getByTestId('cat-q').fill(`Title ${barcode}`)
  await expect(page.locator('.work-row')).toHaveCount(1)
  await page.locator('.work-row').click()
  await page.getByTestId(`hold-${manifestationId}`).click()

  // Owner returns it -> readied for the waiter, shown on the hold shelf.
  await gotoDesk(page)
  await scan(page, 'in', owner, barcode)
  await expect(log(page)).toContainText('set aside for hold')
  await expect(page.getByTestId('hold-shelf')).toContainText(waiter)

  // Fulfil it from the shelf.
  await page.getByTestId('hold-shelf').getByRole('button', { name: 'Check out' }).click()
  await expect(log(page)).toContainText(`checked out to ${waiter}`)
})
