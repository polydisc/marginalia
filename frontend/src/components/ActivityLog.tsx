export interface LogEntry {
  id: number
  kind: 'ok' | 'err'
  text: string
  at: Date
}

export function ActivityLog({ entries }: { entries: LogEntry[] }) {
  if (!entries.length) {
    return (
      <div className="card-pad muted" data-testid="activity-log">
        No activity yet — scan an item to check it out.
      </div>
    )
  }
  return (
    <div className="log" data-testid="activity-log">
      {entries.map((e) => (
        <div key={e.id} className={`logrow ${e.kind}`}>
          <span className="glyph" />
          <time>
            {e.at.toLocaleTimeString('en-GB', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </time>
          <div>{e.text}</div>
        </div>
      ))}
    </div>
  )
}
