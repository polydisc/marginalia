// Inline stroke icons matching the Marginalia prototype (currentColor, 24-grid).
import type { SVGProps } from 'react'

const base: SVGProps<SVGSVGElement> = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
}

export const IconCatalog = (p: SVGProps<SVGSVGElement>) => (
  <svg className="ico" {...base} {...p}>
    <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5z" />
    <path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5z" />
  </svg>
)

export const IconCirc = (p: SVGProps<SVGSVGElement>) => (
  <svg className="ico" {...base} {...p}>
    <path d="M3 7h18M3 12h18M3 17h12" />
  </svg>
)

export const IconPatron = (p: SVGProps<SVGSVGElement>) => (
  <svg className="ico" {...base} {...p}>
    <circle cx="12" cy="8" r="3.2" />
    <path d="M5 20a7 7 0 0 1 14 0" />
  </svg>
)

export const IconBarcode = (p: SVGProps<SVGSVGElement>) => (
  <svg className="ico" {...base} {...p}>
    <path d="M3 5v14M7 5v14M11 5v14M14 5v14M18 5v14M21 5v14" />
  </svg>
)

export const IconSearch = (p: SVGProps<SVGSVGElement>) => (
  <svg className="ico" {...base} strokeWidth={1.8} {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.2-3.2" />
  </svg>
)

export const IconPlus = (p: SVGProps<SVGSVGElement>) => (
  <svg className="ico" {...base} strokeWidth={2} {...p}>
    <path d="M12 5v14M5 12h14" />
  </svg>
)

export const IconChevron = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base} strokeWidth={2.2} {...p}>
    <path d="m9 6 6 6-6 6" />
  </svg>
)
