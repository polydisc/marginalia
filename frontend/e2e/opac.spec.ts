import { test, expect, type Page } from '@playwright/test'

// Unique ids per test so specs stay independent against the shared SQLite file.
let counter = 0
function uid(): string {
  counter += 1
  return `${Date.now().toString().slice(-6)}${counter}`
}

const log = (page: Page) => page.getByTestId('activity-log')

/** Catalog a book on the staff Catalog screen; returns its manifestation id. */
async function catalogBook(page: Page, barcode: string, title: string): Promise<number> {
  await page.getByTestId('nav-catalog').click()
  await expect(page.getByTestId('cat-submit')).toBeVisible()
  await page.getByTestId('cat-title').fill(title)
  await page.getByTestId('cat-author').fill('Author')
  await page.getByTestId('cat-material').selectOption('book')
  await page.getByTestId('cat-isbn').fill('')
  await page.getByTestId('cat-barcode').fill(barcode)
  await page.getByTestId('cat-submit').click()
  await expect(page.getByTestId('cat-msg')).toContainText(`item ${barcode} (available)`)
  const text = (await page.getByTestId('cat-msg').textContent()) ?? ''
  const m = text.match(/manifestation #(\d+)/)
  expect(m, 'manifestation id should appear in the catalog message').not.toBeNull()
  return Number(m![1])
}

/** Register a patron on the staff Circulation Desk. */
async function registerPatron(page: Page, card: string) {
  await page.getByTestId('nav-desk').click()
  await expect(page.getByTestId('desk-go')).toBeVisible()
  await page.getByTestId('reg-card').fill(card)
  await page.getByTestId('reg-category').selectOption('general')
  await page.getByTestId('reg-submit').click()
  await expect(log(page)).toContainText(`Registered patron ${card}`)
}

async function signInToOpac(page: Page, card: string) {
  await page.getByTestId('opac-signin').click()
  await page.getByTestId('opac-signin-card').fill(card)
  await page.getByTestId('opac-signin-submit').click()
  await expect(page.getByTestId('opac-whoami')).toContainText(card)
}

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Circulation Desk' })).toBeVisible()
})

test('search the catalogue, sign in, place a hold, see it in My library, then cancel it', async ({
  page,
}) => {
  const barcode = `B${uid()}`
  const card = `C${uid()}`
  const title = `Opac Title ${barcode}`
  const mid = await catalogBook(page, barcode, title)
  await registerPatron(page, card)

  // Enter the public OPAC and find the title.
  await page.goto('/#/opac')
  await expect(page.getByRole('heading', { name: 'Find your next read' })).toBeVisible()
  await page.getByTestId('opac-q').fill(title)
  await expect(page.getByTestId('opac-works')).toContainText(title)

  // Sign in with the card number (no password) and place a hold on the edition.
  await signInToOpac(page, card)
  await page.getByTestId(`opac-hold-${mid}`).click()
  await expect(page.getByTestId('opac-flash')).toContainText('Hold placed')
  await expect(page.getByTestId('opac-flash')).toContainText('queue')

  // The hold shows up on My library; cancel it there.
  await page.getByTestId('opac-nav-me').click()
  await expect(page.getByTestId('opac-holds')).toContainText(title)
  await page.getByTestId('opac-holds').getByRole('button', { name: 'Cancel' }).click()
  await expect(page.getByTestId('opac-me-flash')).toContainText('cancelled')
  await expect(page.getByTestId('opac-holds-empty')).toBeVisible()
})

test('an unknown card is rejected at sign-in', async ({ page }) => {
  await page.goto('/#/opac')
  await page.getByTestId('opac-signin').click()
  await page.getByTestId('opac-signin-card').fill(`Z${uid()}`)
  await page.getByTestId('opac-signin-submit').click()
  await expect(page.getByTestId('opac-signin-error')).toBeVisible()
  await expect(page.getByTestId('opac-whoami')).toHaveCount(0)
})

test('a suspended patron can browse but is blocked from placing a hold', async ({
  page,
}) => {
  const barcode = `B${uid()}`
  const card = `C${uid()}`
  const title = `Opac Title ${barcode}`
  const mid = await catalogBook(page, barcode, title)
  await registerPatron(page, card)

  // Suspend the patron from the desk.
  await page.getByTestId('nav-desk').click()
  await page.getByTestId('desk-card').fill(card)
  await page.getByTestId('desk-barcode').click() // blur loads the patron
  await expect(page.getByTestId('session-who')).toHaveText(card)
  await page.getByTestId('session-suspend').click()
  await expect(log(page)).toContainText(`${card} is now suspended`)

  // In the OPAC they can still sign in and search, but a hold is refused.
  await page.goto('/#/opac')
  await signInToOpac(page, card)
  await page.getByTestId('opac-q').fill(title)
  await page.getByTestId(`opac-hold-${mid}`).click()
  await expect(page.getByTestId('opac-flash')).toContainText('suspended')

  // Nothing landed on their account.
  await page.getByTestId('opac-nav-me').click()
  await expect(page.getByTestId('opac-holds-empty')).toBeVisible()
})

test('the staff console is still reachable and unchanged', async ({ page }) => {
  // The staff rail offers a link into the OPAC...
  await page.getByTestId('nav-opac').click()
  await expect(page.getByRole('heading', { name: 'Find your next read' })).toBeVisible()
  // ...and the OPAC offers a link back to the staff console.
  await page.getByTestId('opac-staff-link').click()
  await expect(page.getByRole('heading', { name: 'Circulation Desk' })).toBeVisible()
})
