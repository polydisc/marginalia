import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  IconBarcode,
  IconCatalog,
  IconChevron,
  IconCirc,
  IconPatron,
  IconPlus,
  IconSearch,
} from './icons'

const ICONS = {
  IconCatalog,
  IconCirc,
  IconPatron,
  IconBarcode,
  IconSearch,
  IconPlus,
  IconChevron,
}

describe('icons', () => {
  it.each(Object.entries(ICONS))('%s renders an svg and forwards props', (_name, Icon) => {
    const { container } = render(<Icon className="custom" aria-label="x" />)
    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
    // Props passed through to the element (className may merge with the base "ico").
    expect(svg).toHaveAttribute('aria-label', 'x')
    expect(svg?.getAttribute('class')).toContain('custom')
  })
})
