import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ActivityLog, type LogEntry } from './ActivityLog'

const entry = (over: Partial<LogEntry> = {}): LogEntry => ({
  id: 1,
  kind: 'ok',
  text: 'Checked out B001 to C001',
  at: new Date(2026, 5, 26, 13, 20),
  ...over,
})

describe('ActivityLog', () => {
  it('shows an empty-state hint when there is no activity', () => {
    render(<ActivityLog entries={[]} />)
    expect(screen.getByTestId('activity-log')).toHaveTextContent(
      'No activity yet — scan an item to check it out.',
    )
  })

  it('renders one row per entry, newest content and a wall-clock time', () => {
    render(
      <ActivityLog
        entries={[
          entry({ id: 2, kind: 'err', text: '409 ItemNotAvailable', at: new Date(2026, 5, 26, 13, 26) }),
          entry({ id: 1, kind: 'ok', text: 'Registered patron C001', at: new Date(2026, 5, 26, 13, 17) }),
        ]}
      />,
    )

    const log = screen.getByTestId('activity-log')
    const rows = log.querySelectorAll('.logrow')
    expect(rows).toHaveLength(2)
    expect(within(log).getByText('409 ItemNotAvailable')).toBeInTheDocument()
    expect(within(log).getByText('Registered patron C001')).toBeInTheDocument()
    // 24h time, zero-padded.
    expect(within(log).getByText('13:26')).toBeInTheDocument()
  })

  it('tags error rows distinctly from ok rows', () => {
    const { container } = render(
      <ActivityLog entries={[entry({ id: 1, kind: 'err', text: 'boom' })]} />,
    )
    expect(container.querySelector('.logrow.err')).not.toBeNull()
    expect(container.querySelector('.logrow.ok')).toBeNull()
  })
})
