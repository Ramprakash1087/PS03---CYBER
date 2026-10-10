import { fireEvent, render, screen } from '@testing-library/react'
import App from './App'
import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/api/auth-status')) {
          return {
            ok: true,
            json: async () => ({ configured: false, message: 'Authentication not configured' }),
          } as Response
        }
        return {
          ok: true,
          json: async () => ({
            overall_score: 82,
            status: 'Strongly supported',
            summary: { SUPPORTED: 1, CONTRADICTED: 0, QUALIFIED: 0, NOT_FOUND: 0, UNCERTAIN: 0 },
            claims: [
              {
                claim: 'Free shipping on every order',
                verdict: 'SUPPORTED',
                severity: 'low',
                reason: 'The landing page contains the same promise.',
                confidence: 0.9,
                quote: 'Free shipping is available on order totals above $50.',
                source_section: 'Landing page text',
                explanation: 'This claim is directly supported by the page copy.',
                recommended_change: 'Keep the claim as written.',
              },
            ],
            mode: 'SIMULATED',
            simulated: true,
          }),
        } as Response
      }),
    )
  })

  it('shows welcome copy and access options', () => {
    render(<App />)

    expect(screen.getByText(/Every Ad Promise. Verified Against the Page./i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in /i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue as guest/i })).toBeInTheDocument()
  })

  it('renders a report after submitting a guest audit', async () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /continue as guest/i }))
    fireEvent.click(screen.getByRole('button', { name: /check claims/i }))

    expect(await screen.findByText(/ad compliance report/i)).toBeInTheDocument()
    expect(screen.getAllByText('SUPPORTED').length).toBeGreaterThan(0)
    expect(screen.getByText(/recommended ad copy changes/i)).toBeInTheDocument()
  })
})
