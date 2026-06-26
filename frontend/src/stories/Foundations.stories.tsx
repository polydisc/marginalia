import type { Meta, StoryObj } from '@storybook/react'

// Living style guide for the Marginalia design system (system.css). These are
// documentation stories that render the canonical classes — the same ones the
// Circulation Desk and Catalog screens use.
const meta: Meta = {
  title: 'Design System/Foundations',
  parameters: { a11y: { test: 'todo' } },
}
export default meta

type Story = StoryObj

export const Buttons: Story = {
  render: () => (
    <div className="row wrap">
      <button className="btn">Check out</button>
      <button className="btn btn-secondary">Return</button>
      <button className="btn btn-ghost">Renew</button>
      <button className="btn btn-danger">Withdraw</button>
      <button className="btn btn-sm">Small</button>
      <button className="btn" disabled>
        Disabled
      </button>
    </div>
  ),
}

const ITEM_STATES = [
  'available',
  'on_loan',
  'on_hold_shelf',
  'in_repair',
  'lost',
  'withdrawn',
] as const

export const StatusPills: Story = {
  render: () => (
    <div className="row wrap">
      {ITEM_STATES.map((s) => (
        <span key={s} className={`pill ${s}`}>
          <span className="dot" />
          {s.replace(/_/g, ' ')}
        </span>
      ))}
    </div>
  ),
}

export const Chips: Story = {
  render: () => (
    <div className="row wrap">
      <span className="chip work">Work</span>
      <span className="chip manifestation">Manifestation</span>
      <span className="chip item">Item</span>
    </div>
  ),
}

export const FormControls: Story = {
  render: () => (
    <div className="grid" style={{ maxWidth: 360 }}>
      <label className="field">
        <span className="lbl">Patron card</span>
        <input className="input mono" defaultValue="C001" />
      </label>
      <label className="field">
        <span className="lbl">Material type</span>
        <select className="select" defaultValue="book">
          <option value="book">book</option>
          <option value="reference">reference</option>
          <option value="audiovisual">audiovisual</option>
        </select>
      </label>
      <form className="scan" onSubmit={(e) => e.preventDefault()}>
        <span className="mono muted" style={{ paddingLeft: 4 }}>
          ⌗
        </span>
        <input placeholder="Scan a barcode…" defaultValue="B001" />
        <button className="btn btn-sm" type="submit">
          Enter
        </button>
      </form>
      <div className="seg" role="tablist">
        <button role="tab" aria-selected="true">
          Check out
        </button>
        <button role="tab" aria-selected="false">
          Return
        </button>
        <button role="tab" aria-selected="false">
          Renew
        </button>
      </div>
    </div>
  ),
}

export const Card: Story = {
  render: () => (
    <div className="card" style={{ maxWidth: 420 }}>
      <div className="card-head">
        <h3>Hold shelf</h3>
        <div className="spacer" />
        <span className="pill on_hold_shelf">
          <span className="dot" />
          ready
        </span>
      </div>
      <div className="card-pad muted">No holds waiting on the shelf.</div>
    </div>
  ),
}
