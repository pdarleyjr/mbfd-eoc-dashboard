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
      label: 'FPL Regional Grid Demand',
      value: null,
      unavailable: true,
      source: 'EIA-930 · FPL regional; not local outage data',
      updated_at: null,
      detail_category: 'power_grid_status',
    },
  ],
  records: [],
  source_health: [],
  health_summary: {
    critical_healthy: 6,
    critical_total: 6,
    all_healthy: 0,
    all_total: 0,
    unavailable_critical: [],
  },
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
    {
      ...record('call', 'pulsepoint_call', {
        state: 'active',
        call_type_code: 'ME',
        address: 'COLLINS AVE, MIAMI BEACH, FL',
        units: [
          {id: 'CPT5', status: 'On Scene', cleared_at: null},
          {id: 'E2', status: 'Available on Radio', cleared_at: null},
          {id: 'R22', status: 'Transport', cleared_at: null},
          {id: 'R11', status: 'Transport Arrived', cleared_at: null},
          {id: 'E1', status: 'Dispatched', cleared_at: null},
        ],
        agency: 'X1012',
        disclaimer: 'PulsePoint advisory feed — not official CAD',
      }),
      title: 'Medical Emergency',
      geography: {type: 'Point', coordinates: [-80.12049, 25.83412]},
    },
    {
      ...record('call-none', 'pulsepoint_call', {
        state: 'recent',
        call_type_code: 'FA',
        address: 'WASHINGTON AVE, MIAMI BEACH, FL',
        units: [],
        agency: 'X1012',
        disclaimer: 'PulsePoint advisory feed — not official CAD',
      }),
      title: 'Fire Alarm',
    },
    record('forecast', 'forecast', {
      forecast_kind: 'hourly',
      shortForecast: 'Scattered storms',
      temperature: 88,
      temperatureUnit: 'F',
    }),
    {
      ...record('observation', 'weather_observation', {
        station_id: 'KMIA',
        station_name: 'Miami International Airport',
        temperature: {value: 30, unitCode: 'wmoUnit:degC'},
        relativeHumidity: {value: 72, unitCode: 'wmoUnit:percent'},
        windSpeed: {value: 20, unitCode: 'wmoUnit:km_h-1'},
        windGust: {value: 30, unitCode: 'wmoUnit:km_h-1'},
        visibility: {value: 16093.4, unitCode: 'wmoUnit:m'},
        barometricPressure: {value: 101320, unitCode: 'wmoUnit:Pa'},
        precipitationLastHour: {value: 2.54, unitCode: 'wmoUnit:mm'},
      }),
      observed_at: '2026-07-27T13:59:00Z',
    },
    record('water', 'coastal_observation', {product: 'water_level', v: '1.2'}),
    {
      ...record('water-previous', 'coastal_observation', {product: 'water_level', v: '1.1'}),
      observed_at: '2026-07-27T13:52:00Z',
    },
    record('predicted-water', 'coastal_observation', {
      product: 'predicted_water_level',
      v: '0.9',
    }),
    {
      ...record('high-tide', 'coastal_observation', {
        product: 'tide_predictions',
        tide_type: 'H',
        v: '1.35',
      }),
      observed_at: '2026-07-27T17:00:00Z',
    },
    {
      ...record('low-tide', 'coastal_observation', {
        product: 'tide_predictions',
        tide_type: 'L',
        v: '0.1',
      }),
      observed_at: '2026-07-27T20:00:00Z',
    },
    record('wind', 'coastal_observation', {product: 'wind', s: 12}),
    record('alert', 'weather_alert'),
    {
      ...record(
        'road',
        'lane_closure',
        {
          USER_status_desc: 'Active',
          USER_permit_number: 'ROW-2026-0042',
          USER_description:
            'Water-main extension work restricts the eastbound lane. Local access remains open.',
          USER_main_address_line_1: '1881 WASHINGTON AVE',
          USER_main_address_line_2: 'MIAMI BEACH, FL 33139',
          USER_issue_date: '2026-07-27T12:00:00Z',
          USER_expiration_date: '2026-07-31T21:00:00Z',
          text: `Grounded official source excerpt ${'with readable details '.repeat(50)}`,
        },
        true,
      ),
      title: '1881 WASHINGTON AVE',
    },
    {
      ...record('notice', 'official_notice', {
        text: 'Miami-Dade DEM is monitoring potential Atlantic storms. Officials will provide updates if systems threaten the county.',
      }),
      title: 'Miami-Dade DEM monitors Atlantic storms',
    },
    record('shelter', 'open_shelter'),
    record('hospital', 'hospital'),
    {
      ...record('power', 'power_grid_status', {
        respondent: 'FPL',
        metric_type: 'D',
        metric_name: 'Demand',
        value: 23418,
        unit: 'megawatthours',
        period: '2026-07-28T09-04:00',
        geographic_scope: 'Florida Power & Light balancing authority',
        scope_note: 'Regional grid indicator; not a Miami Beach customer-outage count',
      }),
      title: 'FPL regional grid demand',
    },
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
      name: /FPL Regional Grid Demand/i,
    })
    expect(within(powerTile).getByText('Not available')).toBeVisible()
    expect(screen.getByRole('heading', {name: 'Active Calls'})).toBeVisible()
    expect(
      screen.queryByText('PulsePoint advisory feed — not official CAD'),
    ).not.toBeInTheDocument()
  })

  it('renders operational PulsePoint, road, notice, and regional-grid content', () => {
    queryResult = {...queryResult, data: richSummary}
    renderDashboard()

    const pulseCall = screen.getByRole('button', {
      name: /Medical Emergency.*ME.*COLLINS AVE/i,
    })
    expect(within(pulseCall).getByText('Active')).toBeVisible()
    expect(within(pulseCall).getByText('Live')).toBeVisible()
    expect(within(pulseCall).getByText('CPT5')).toBeVisible()
    expect(within(pulseCall).getByText('On Scene')).toBeVisible()
    expect(within(pulseCall).getByText('+1')).toBeVisible()
    expect(screen.getByText('No units reported')).toBeVisible()
    expect(screen.getByText('Recent')).toBeVisible()

    const road = screen.getByRole('button', {name: /1881 WASHINGTON AVE.*ROW-2026-0042/i})
    expect(within(road).getByText(/Water-main extension work/)).toBeVisible()
    expect(within(road).getByText('Active')).toBeVisible()
    expect(screen.getByText(/Miami-Dade DEM is monitoring potential Atlantic storms/)).toBeVisible()
    expect(
      screen.getByText('Regional grid indicator; not a Miami Beach customer-outage count'),
    ).toBeVisible()
    expect(
      screen.getByText(
        'Regional grid demand is shown here. Local customer outages are available through FPL Power Tracker.',
      ),
    ).toBeVisible()
    expect(screen.getByRole('link', {name: 'Open FPL Power Tracker'})).toHaveAttribute(
      'href',
      'https://www.fpl.com/powertracker',
    )

    fireEvent.click(pulseCall)
    expect(useDashboardStore.getState().selectedRecordId).toBe('call')
    const drawer = document.querySelector<HTMLElement>('.detail-drawer')
    expect(drawer).not.toBeNull()
    if (!drawer) throw new Error('PulsePoint detail drawer is missing')
    expect(within(drawer).getByText('Available on Radio')).toBeVisible()
    expect(within(drawer).getByText('Transport Arrived')).toBeVisible()
    expect(within(drawer).getByText('PulsePoint advisory feed — not official CAD')).toBeVisible()
  })

  it('separates observations, forecasts, and tide decisions and opens Radar mode', () => {
    queryResult = {...queryResult, data: richSummary}
    renderDashboard()

    expect(screen.getByText('Observed now')).toBeVisible()
    expect(screen.getByText('86°F')).toBeVisible()
    expect(screen.getByText(/Humidity 72%/)).toBeVisible()
    expect(screen.getByText('Next-hour forecast')).toBeVisible()
    expect(screen.getByText('Scattered storms')).toBeVisible()
    expect(screen.getByText(/Wind 12 mph · Gust 19 mph/)).toBeVisible()
    expect(screen.getByText(/Visibility 10 mi/)).toBeVisible()
    expect(screen.getByText(/Pressure 29.92 inHg/)).toBeVisible()
    expect(screen.getByText(/Rain 0.10 in/)).toBeVisible()
    expect(screen.getByText(/Observed 1.20 m/)).toBeVisible()
    expect(screen.getByText(/Predicted 0.90 m/)).toBeVisible()
    expect(screen.getByText(/Anomaly \+0.30 m/)).toBeVisible()
    expect(screen.getByText(/Rising/)).toBeVisible()
    expect(screen.getByText(/Next high/)).toBeVisible()
    expect(screen.getByText(/Next low/)).toBeVisible()
    expect(screen.getByText('1.35 m')).toBeVisible()
    expect(screen.getByText('0.10 m')).toBeVisible()

    fireEvent.click(screen.getByRole('button', {name: 'View Radar'}))
    expect(useDashboardStore.getState().mapMode).toBe('radar')
  })

  it('shows Immediate Attention only for action-relevant conditions', () => {
    const clear = renderDashboard()
    expect(screen.queryByRole('region', {name: 'Immediate Attention'})).not.toBeInTheDocument()
    clear.unmount()

    queryResult = {
      ...queryResult,
      data: {
        ...richSummary,
        metadata: {...richSummary.metadata, stale: false},
        records: [
          ...richSummary.records.filter((item) => item.id !== 'alert'),
          {
            ...record('flash-flood', 'weather_alert', {
              event: 'Flash Flood Warning',
              severity: 'Severe',
              urgency: 'Immediate',
              certainty: 'Observed',
            }),
            title: 'Flash Flood Warning for coastal Miami-Dade',
          },
        ],
      },
    }
    renderDashboard()

    const attention = screen.getByRole('region', {name: 'Immediate Attention'})
    expect(within(attention).getByText(/Flash Flood Warning for coastal Miami-Dade/)).toBeVisible()
  })

  it('renders honest fallback values for partial operational records', () => {
    const edgeSummary: DashboardSummary = {
      ...baseSummary,
      kpis: [],
      records: [
        {
          ...record('call-recent-edge', 'pulsepoint_call', {
            state: 'recent',
            units: [],
          }),
          title: 'Recent advisory call',
        },
        {
          ...record(
            'call-active-edge',
            'pulsepoint_call',
            {
              state: 'active',
              units: [null, {id: 42}, {id: 'R1', status: '', cleared_at: '2026-07-27T14:02:00Z'}],
            },
            true,
          ),
          title: 'Active advisory call',
          observed_at: null,
          published_at: '2026-07-27T13:57:00Z',
          stale_reason: null,
        },
        {
          ...record('road-edge', 'lane_closure'),
          title: 'Causeway status report',
        },
        {
          ...record('notice-edge', 'official_notice'),
          title: 'Official update without a supplied summary',
        },
        {
          ...record('power-edge', 'power_grid_status', {
            value: 'unavailable',
            unit: 'watts',
          }),
          title: 'FPL regional grid metric',
        },
      ],
      source_health: [
        {
          source_id: 'empty-source',
          source_name: 'Empty official source',
          state: 'healthy',
          last_attempt: '2026-07-27T14:00:00Z',
          last_success: '2026-07-27T14:00:00Z',
          last_authoritative_observation: null,
          current_data_age_seconds: 0,
          poll_interval_seconds: 60,
          consecutive_failures: 0,
          last_known_good: false,
          authority_level: 'authoritative',
          circuit_breaker_state: 'closed',
          schema_version: 1,
          message: 'No current records returned by source',
        },
      ],
    }
    queryResult = {...queryResult, data: edgeSummary}
    renderDashboard()

    const call = screen.getByRole('button', {name: /Active advisory call/i})
    expect(within(call).getByText('Stale')).toBeVisible()
    expect(within(call).getByText('Address unavailable')).toBeVisible()
    expect(within(call).getByText('R1')).toBeVisible()
    expect(within(call).getByText('Status not reported')).toBeVisible()
    const trafficPanel = document.querySelector<HTMLElement>('.traffic-panel')
    expect(trafficPanel).not.toBeNull()
    if (!trafficPanel) throw new Error('Traffic panel is missing')
    expect(
      within(trafficPanel).getByRole('button', {name: /Causeway status report/i}),
    ).toHaveTextContent('Status reported by source')
    expect(screen.getByText('Official update without a supplied summary')).toBeVisible()
    expect(screen.getByText('Value unavailable')).toBeVisible()

    fireEvent.click(call)
    const drawer = document.querySelector<HTMLElement>('.detail-drawer')
    expect(drawer).not.toBeNull()
    if (!drawer) throw new Error('Partial-record detail drawer is missing')
    expect(drawer.querySelector('.degraded-banner')).toHaveTextContent('Source is stale.')
    expect(within(drawer).getByText('Status not reported')).toBeVisible()
    expect(within(drawer).getByText(/Cleared/)).toBeVisible()
    fireEvent.click(screen.getByRole('button', {name: 'Close record details'}))
    fireEvent.click(screen.getByRole('button', {name: 'Open dashboard data-source health'}))
    expect(screen.getByText('No retained records')).toBeVisible()
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

    expect(
      screen.getAllByText(
        'Miami-Dade DEM is monitoring potential Atlantic storms. Officials will provide updates if systems threaten the county.',
      )[0],
    ).toBeVisible()
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
    fireEvent.click(screen.getByRole('radio', {name: /Compact/}))
    expect(useDashboardStore.getState().density).toBe('compact')
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
