import {QueryClient, QueryClientProvider} from '@tanstack/react-query'
import {fireEvent, render, screen, within} from '@testing-library/react'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import {useDashboardStore} from '../store/dashboardStore'
import type {CanonicalRecord, DashboardSummary} from '../types'
import {Dashboard} from './Dashboard'

const baseSummary: DashboardSummary = {
  metadata: {
    generated_at: '2026-07-27T14:00:00Z',
    source_observation_time: null,
    data_age_seconds: null,
    stale: false,
    source_authority: [],
    source_health: 'unavailable',
    last_successful_refresh: null,
    empty_state: 'No current records returned by source',
  },
  kpis: [
    {
      id: 'power',
      label: 'Miami-Dade Power Outage Percentage',
      value: null,
      unavailable: true,
      source: 'FDEM public summary',
      updated_at: null,
      detail_category: 'power_outage_summary',
    },
  ],
  records: [],
  source_health: [],
}

let queryResult: {
  data: DashboardSummary | undefined
  isLoading: boolean
  isError: boolean
  dataUpdatedAt: number
}

vi.mock('../hooks/useDashboard', () => ({
  useDashboard: () => queryResult,
}))

vi.mock('./OperationalMap', () => ({
  OperationalMap: ({records}: {records: CanonicalRecord[]}) => (
    <section aria-label="Operational map test double">{records.length} map records</section>
  ),
}))

function record(
  id: string,
  category: string,
  payload: Record<string, unknown> = {},
  stale = false,
): CanonicalRecord {
  return {
    id,
    source_id: `source-${id}`,
    source_name: `Official source ${id}`,
    source_type: category === 'pulsepoint_call' ? 'pulsepoint_advisory' : 'official_api',
    authority_level: category === 'pulsepoint_call' ? 'advisory' : 'authoritative',
    source_record_id: id,
    source_url: 'https://example.gov/data',
    title: `Record ${id}`,
    category,
    observed_at: '2026-07-27T13:58:00Z',
    published_at: null,
    retrieved_at: '2026-07-27T14:00:00Z',
    expires_at: null,
    stale,
    stale_reason: stale ? 'Refresh failed' : null,
    confidence: 1,
    geography: {},
    zip_scope: ['33139'],
    raw_snapshot_hash: 'a'.repeat(64),
    schema_version: 1,
    payload,
  }
}

const richSummary: DashboardSummary = {
  ...baseSummary,
  metadata: {
    ...baseSummary.metadata,
    stale: true,
    source_health: 'delayed',
    source_authority: ['authoritative', 'advisory'],
  },
  kpis: [
    {
      id: 'roads',
      label: 'Road & Access Incidents',
      value: 1,
      unavailable: false,
      source: 'Official public traffic sources',
      updated_at: '2026-07-27T14:00:00Z',
      detail_category: 'lane_closure',
    },
  ],
  records: [
    record('call', 'pulsepoint_call', {state: 'active', call_type: 'Medical'}),
    record('forecast', 'forecast', {
      forecast_kind: 'hourly',
      shortForecast: 'Scattered storms',
      temperature: 88,
      temperatureUnit: 'F',
    }),
    record('water', 'coastal_observation', {product: 'water_level', v: 1.2}),
    record('wind', 'coastal_observation', {product: 'wind', s: 12}),
    record('alert', 'weather_alert'),
    record(
      'road',
      'lane_closure',
      {
        status: 'closed',
        text: `Grounded official source excerpt ${'with readable details '.repeat(50)}`,
      },
      true,
    ),
    record('notice', 'official_notice', {text: 'Short official source excerpt.'}),
    record('shelter', 'open_shelter'),
    record('hospital', 'hospital'),
    record('power', 'power_outage_summary', {Pct_Out: 1.25}),
    record('transit', 'transit', {schedule_only: true}),
  ],
  source_health: [
    {
      source_id: 'official-source',
      source_name: 'Official Source',
      state: 'delayed',
      last_attempt: '2026-07-27T14:00:00Z',
      last_success: '2026-07-27T13:59:00Z',
      last_authoritative_observation: '2026-07-27T13:58:00Z',
      current_data_age_seconds: 120,
      poll_interval_seconds: 45,
      consecutive_failures: 1,
      last_known_good: true,
      authority_level: 'authoritative',
      circuit_breaker_state: 'closed',
      schema_version: 1,
      message: 'Showing last-known-good data',
    },
  ],
}

function renderDashboard() {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}})
  return render(
    <QueryClientProvider client={client}>
      <Dashboard />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  useDashboardStore.getState().reset()
  queryResult = {
    data: baseSummary,
    isLoading: false,
    isError: false,
    dataUpdatedAt: 0,
  }
})

describe('Dashboard', () => {
  it('uses the supplied MBFD logo and explicit unavailable language', () => {
    renderDashboard()
    expect(screen.getByAltText('Miami Beach Fire Department')).toBeVisible()
    expect(
      screen.getByRole('heading', {name: 'Miami Beach Emergency Management Dashboard'}),
    ).toBeVisible()
    const powerTile = screen.getByRole('button', {
      name: /Miami-Dade Power Outage Percentage/i,
    })
    expect(within(powerTile).getByText('Not available')).toBeVisible()
    expect(screen.getByText('PulsePoint advisory feed — not official CAD')).toBeVisible()
  })

  it('renders rich official-source content and opens record details', () => {
    queryResult = {...queryResult, data: richSummary}
    useDashboardStore.getState().selectRecord('road')
    renderDashboard()

    expect(screen.getByText('Scattered storms')).toBeVisible()
    expect(screen.getAllByText('Showing cached information', {exact: false})[0]).toBeVisible()
    expect(screen.getByText('Refresh failed', {exact: false})).toBeVisible()
    expect(screen.getByRole('heading', {name: 'Source excerpt'})).toBeVisible()
    fireEvent.click(screen.getByText('Show full extracted source text'))
    expect(screen.getAllByText(/Grounded official source excerpt/).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', {name: 'Open official source'})).toHaveAttribute(
      'href',
      'https://example.gov/data',
    )
    fireEvent.click(screen.getByRole('button', {name: 'Close record details'}))
    expect(useDashboardStore.getState().selectedRecordId).toBeNull()
  })

  it('keeps a short source excerpt readable without an unnecessary expander', () => {
    queryResult = {...queryResult, data: richSummary}
    useDashboardStore.getState().selectRecord('notice')
    renderDashboard()

    expect(screen.getByText('Short official source excerpt.')).toBeVisible()
    expect(screen.queryByText('Show full extracted source text')).not.toBeInTheDocument()
  })

  it('opens source health and settings through keyboard-accessible controls', () => {
    queryResult = {...queryResult, data: richSummary}
    useDashboardStore.getState().setSourceDrawerOpen(true)
    const sourceView = renderDashboard()

    expect(screen.getByText('Showing last-known-good data')).toBeVisible()
    expect(screen.getByText('Retained')).toBeVisible()
    fireEvent.click(screen.getByRole('button', {name: 'Close data-source health'}))
    sourceView.unmount()

    useDashboardStore.getState().reset()
    useDashboardStore.getState().setSettingsOpen(true)
    renderDashboard()
    fireEvent.click(screen.getByRole('radio', {name: /Comfortable/}))
    expect(useDashboardStore.getState().density).toBe('comfortable')
    fireEvent.click(screen.getByRole('button', {name: 'Close settings'}))
  })

  it('selects the first matching record from a KPI tile', () => {
    queryResult = {...queryResult, data: richSummary}
    renderDashboard()

    fireEvent.click(screen.getByRole('button', {name: /Road & Access Incidents/}))
    expect(useDashboardStore.getState().selectedRecordId).toBe('road')
  })

  it('shows a loading shell and an honest uncached error', () => {
    queryResult = {...queryResult, data: undefined, isLoading: true}
    const first = renderDashboard()
    expect(screen.getByLabelText('Loading emergency management dashboard')).toBeVisible()
    first.unmount()

    queryResult = {...queryResult, isLoading: false, isError: true}
    renderDashboard()
    expect(
      screen.getByText(
        'Source temporarily unavailable. No cached dashboard snapshot could be loaded.',
      ),
    ).toBeVisible()
  })
})
