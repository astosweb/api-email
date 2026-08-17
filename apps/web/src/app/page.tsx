async function getHealth() {
  const apiUrl = process.env.API_URL ?? 'http://localhost:4000';
  try {
    const res = await fetch(`${apiUrl}/health`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function getEmails() {
  const apiUrl = process.env.INTERNAL_API_URL ?? process.env.API_URL ?? 'http://localhost:4000';
  try {
    const res = await fetch(`${apiUrl}/v1/internal/emails?limit=20`, {
      cache: 'no-store',
      headers: process.env.INTERNAL_API_TOKEN
        ? { Authorization: `Bearer ${process.env.INTERNAL_API_TOKEN}` }
        : {},
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function DashboardPage() {
  const health = await getHealth();
  const emails = await getEmails();

  return (
    <main style={{ maxWidth: 960, margin: '0 auto', padding: '2rem' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', margin: 0 }}>API Email Dashboard</h1>
        <p style={{ color: '#94a3b8', marginTop: '0.5rem' }}>
          Production email infrastructure monitoring
        </p>
      </header>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <StatusCard label="API" status={health ? 'healthy' : 'unavailable'} />
        <StatusCard label="Database" status={health?.details?.database?.status === 'up' ? 'healthy' : 'unknown'} />
        <StatusCard label="Redis" status={health?.details?.redis?.status === 'up' ? 'healthy' : 'unknown'} />
        <StatusCard label="Queue waiting" status={String(health?.details?.queue?.waiting ?? 0)} />
      </section>

      <section>
        <h2 style={{ fontSize: '1.25rem' }}>Recent Emails</h2>
        {emails.length === 0 ? (
          <p style={{ color: '#94a3b8' }}>No emails yet. Send via POST /v1/emails</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155', textAlign: 'left' }}>
                <th style={{ padding: '0.75rem' }}>ID</th>
                <th style={{ padding: '0.75rem' }}>To</th>
                <th style={{ padding: '0.75rem' }}>Subject</th>
                <th style={{ padding: '0.75rem' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {emails.map((email: { id: string; to: string[]; subject: string; status: string }) => (
                <tr key={email.id} style={{ borderBottom: '1px solid #1e293b' }}>
                  <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.85rem' }}>{email.id.slice(0, 8)}…</td>
                  <td style={{ padding: '0.75rem' }}>{email.to.join(', ')}</td>
                  <td style={{ padding: '0.75rem' }}>{email.subject}</td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: 4,
                      fontSize: '0.85rem',
                      background: statusColor(email.status),
                    }}>
                      {email.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}

function StatusCard({ label, status }: { label: string; status: string }) {
  return (
    <div style={{ background: '#1e293b', borderRadius: 8, padding: '1rem' }}>
      <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{label}</div>
      <div style={{ fontSize: '1.25rem', marginTop: '0.25rem' }}>{status}</div>
    </div>
  );
}

function statusColor(status: string): string {
  switch (status) {
    case 'sent':
    case 'delivered':
      return '#166534';
    case 'queued':
    case 'processing':
      return '#854d0e';
    case 'failed':
    case 'bounced':
      return '#991b1b';
    default:
      return '#334155';
  }
}
