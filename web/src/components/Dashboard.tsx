import {
  Button,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerHeaderTitle,
  Radio,
  RadioGroup,
  Skeleton,
  SkeletonItem,
  Tooltip,
} from '@fluentui/react-components'
import {
  ArrowMaximize24Regular,
  Database24Regular,
  Dismiss24Regular,
  Settings24Regular,
  ShieldError24Regular,
} from '@fluentui/react-icons'
import {lazy, Suspense, useCallback, useEffect, useMemo, useState} from 'react'
import {useDashboard} from '../hooks/useDashboard'
import {formatAge, localTime, recordTime, valueText} from '../lib/format'
import {useDashboardStore} from '../store/dashboardStore'
import type {CanonicalRecord} from '../types'
import {StatusPill} from './StatusPill'

const OperationalMap = lazy(async () => {
  const module = await import('./OperationalMap')
  return {default: module.OperationalMap}
})

function Clock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  return (
    <time dateTime={now.toISOString()}>
      {new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/New_York',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short',
      }).format(now)}
    </time>
  )
}

function Panel({
  title,
  subtitle,
  children,
  className = '',
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-title-row">
        <h2>{title}</h2>
        {subtitle && <span>{subtitle}</span>}
      </div>
      {children}
    </section>
  )
}

function RecordList({
  records,
  empty,
  limit = 4,
}: {
  records: CanonicalRecord[]
  empty: string
  limit?: number
}) {
  const selectRecord = useDashboardStore((state) => state.selectRecord)
  if (!records.length)
    return (
      <div className="honest-empty">
        <ShieldError24Regular aria-hidden />
        <span>{empty}</span>
      </div>
    )
  return (
    <ul className="record-list">
      {records.slice(0, limit).map((record) => (
        <li key={record.id}>
          <button type="button" onClick={() => selectRecord(record.id)}>
            <span className={`record-dot authority-${record.authority_level}`} aria-hidden />
            <span className="record-copy">
              <strong>{record.title}</strong>
              <small>
                {record.source_name} · {recordTime(record)}
              </small>
            </span>
            {record.stale && <span className="stale-tag">Stale</span>}
          </button>
        </li>
      ))}
    </ul>
  )
}

function WeatherCoastal({records}: {records: CanonicalRecord[]}) {
  const forecast = records.find(
    (record) => record.category === 'forecast' && record.payload.forecast_kind === 'hourly',
  )
  const alert = records.find((record) => record.category === 'weather_alert')
  const water = records.find(
    (record) =>
      record.category === 'coastal_observation' && record.payload.product === 'water_level',
  )
  const wind = records.find(
    (record) => record.category === 'coastal_observation' && record.payload.product === 'wind',
  )
  return (
    <Panel
      title="Weather & Coastal Conditions"
      subtitle="NWS · NOAA CO-OPS"
      className="weather-panel"
    >
      <div className="weather-primary">
        <div>
          <span>Current forecast</span>
          <strong>{forecast ? valueText(forecast.payload.shortForecast) : 'Not available'}</strong>
          <small>
            {forecast
              ? `${valueText(forecast.payload.temperature)}°${valueText(forecast.payload.temperatureUnit)}`
              : 'Source status is shown below'}
          </small>
        </div>
        <div className={alert ? 'weather-alert active' : 'weather-alert'}>
          <span>Active NWS alert</span>
          <strong>{alert?.title ?? 'No current records returned by source'}</strong>
        </div>
      </div>
      <div className="condition-strip">
        <div>
          <span>Water level</span>
          <strong>{water ? valueText(water.payload.v) : '—'}</strong>
          <small>{water ? 'Observed · MLLW' : 'Not available'}</small>
        </div>
        <div>
          <span>Wind</span>
          <strong>{wind ? valueText(wind.payload.s) : '—'}</strong>
          <small>{wind ? 'Observed' : 'Not available'}</small>
        </div>
        <div>
          <span>Station</span>
          <strong>8723214</strong>
          <small>Virginia Key</small>
        </div>
      </div>
    </Panel>
  )
}

function SourceDrawer({
  health,
}: {
  health: ReturnType<typeof useDashboard>['data'] extends infer T
    ? T extends {source_health: infer H}
      ? H
      : never
    : never
}) {
  const open = useDashboardStore((state) => state.sourceDrawerOpen)
  const setOpen = useDashboardStore((state) => state.setSourceDrawerOpen)
  return (
    <Drawer
      type="overlay"
      position="end"
      size="large"
      open={open}
      onOpenChange={(_, data) => setOpen(data.open)}
    >
      <DrawerHeader>
        <DrawerHeaderTitle
          action={
            <Button
              appearance="subtle"
              icon={<Dismiss24Regular />}
              aria-label="Close data-source health"
              onClick={() => setOpen(false)}
            />
          }
        >
          Dashboard Data-Source Health
        </DrawerHeaderTitle>
      </DrawerHeader>
      <DrawerBody>
        <div className="source-health-table" role="table" aria-label="Data source status">
          {Array.isArray(health) && health.length ? (
            health.map((source) => (
              <article key={source.source_id} className="source-health-row">
                <div>
                  <strong>{source.source_name}</strong>
                  <span>
                    {source.authority_level} · schema v{source.schema_version}
                  </span>
                </div>
                <StatusPill state={source.state} />
                <dl>
                  <div>
                    <dt>Last attempt</dt>
                    <dd>{localTime(source.last_attempt)}</dd>
                  </div>
                  <div>
                    <dt>Last success</dt>
                    <dd>{localTime(source.last_success)}</dd>
                  </div>
                  <div>
                    <dt>Authoritative observation</dt>
                    <dd>{localTime(source.last_authoritative_observation)}</dd>
                  </div>
                  <div>
                    <dt>Current data age</dt>
                    <dd>{formatAge(source.current_data_age_seconds)}</dd>
                  </div>
                  <div>
                    <dt>Poll interval</dt>
                    <dd>{source.poll_interval_seconds} seconds</dd>
                  </div>
                  <div>
                    <dt>Consecutive failures</dt>
                    <dd>{source.consecutive_failures}</dd>
                  </div>
                  <div>
                    <dt>Last-known-good</dt>
                    <dd>{source.last_known_good ? 'Retained' : 'No retained records'}</dd>
                  </div>
                  <div>
                    <dt>Circuit breaker</dt>
                    <dd>{source.circuit_breaker_state}</dd>
                  </div>
                </dl>
                {source.message && <p>{source.message}</p>}
              </article>
            ))
          ) : (
            <div className="honest-empty">Source health has not been reported yet.</div>
          )}
        </div>
      </DrawerBody>
    </Drawer>
  )
}

function SettingsDrawer() {
  const open = useDashboardStore((state) => state.settingsOpen)
  const setOpen = useDashboardStore((state) => state.setSettingsOpen)
  const density = useDashboardStore((state) => state.density)
  const setDensity = useDashboardStore((state) => state.setDensity)
  return (
    <Drawer
      type="overlay"
      position="end"
      open={open}
      onOpenChange={(_, data) => setOpen(data.open)}
    >
      <DrawerHeader>
        <DrawerHeaderTitle
          action={
            <Button
              appearance="subtle"
              icon={<Dismiss24Regular />}
              aria-label="Close settings"
              onClick={() => setOpen(false)}
            />
          }
        >
          Dashboard settings
        </DrawerHeaderTitle>
      </DrawerHeader>
      <DrawerBody>
        <fieldset className="settings-fieldset">
          <legend>Display density</legend>
          <RadioGroup
            value={density}
            onChange={(_, data) =>
              setDensity(data.value === 'comfortable' ? 'comfortable' : 'compact')
            }
          >
            <Radio value="compact" label="Compact — maximum operational context" />
            <Radio value="comfortable" label="Comfortable — larger spacing and type" />
          </RadioGroup>
        </fieldset>
        <p className="settings-note">
          Map-layer controls are available directly on the map so they remain keyboard and touch
          accessible.
        </p>
      </DrawerBody>
    </Drawer>
  )
}

function DetailDrawer({record}: {record: CanonicalRecord | undefined}) {
  const selectRecord = useDashboardStore((state) => state.selectRecord)
  const sourceText = typeof record?.payload.text === 'string' ? record.payload.text : null
  const payloadEntries = record
    ? Object.entries(record.payload)
        .filter(
          ([key, value]) =>
            key !== 'text' && ['string', 'number', 'boolean'].includes(typeof value),
        )
        .slice(0, 24)
    : []
  return (
    <Drawer
      type="overlay"
      position="end"
      size="large"
      className="detail-drawer"
      open={Boolean(record)}
      onOpenChange={(_, data) => {
        if (!data.open) selectRecord(null)
      }}
    >
      {record && (
        <>
          <DrawerHeader>
            <DrawerHeaderTitle
              action={
                <Button
                  appearance="subtle"
                  icon={<Dismiss24Regular />}
                  aria-label="Close record details"
                  onClick={() => selectRecord(null)}
                />
              }
            >
              {record.title}
            </DrawerHeaderTitle>
          </DrawerHeader>
          <DrawerBody>
            <div className="record-provenance">
              <span className={`authority-badge authority-badge-${record.authority_level}`}>
                {record.authority_level}
              </span>
              <span>{record.source_name}</span>
            </div>
            {record.stale && (
              <div className="degraded-banner">
                Showing cached information. {record.stale_reason ?? 'Source is stale.'}
              </div>
            )}
            <dl className="record-details">
              <div>
                <dt>Source</dt>
                <dd>{record.source_name}</dd>
              </div>
              <div>
                <dt>Authority</dt>
                <dd>{record.authority_level}</dd>
              </div>
              <div>
                <dt>Source observation</dt>
                <dd>{localTime(record.observed_at ?? record.published_at)}</dd>
              </div>
              <div>
                <dt>Retrieved</dt>
                <dd>{localTime(record.retrieved_at)}</dd>
              </div>
              <div>
                <dt>Source record ID</dt>
                <dd>{record.source_record_id}</dd>
              </div>
            </dl>
            <div className="payload-grid">
              {payloadEntries.map(([key, value]) => (
                <div key={key}>
                  <span>{key.replaceAll('_', ' ')}</span>
                  <strong>{valueText(value)}</strong>
                </div>
              ))}
            </div>
            {sourceText && (
              <section className="source-excerpt" aria-labelledby="source-excerpt-heading">
                <h3 id="source-excerpt-heading">Source excerpt</h3>
                <p>{sourceText.slice(0, 700)}</p>
                {sourceText.length > 700 && (
                  <details>
                    <summary>Show full extracted source text</summary>
                    <p>{sourceText}</p>
                  </details>
                )}
              </section>
            )}
            <a href={record.source_url} target="_blank" rel="noreferrer" className="source-link">
              Open official source
            </a>
          </DrawerBody>
        </>
      )}
    </Drawer>
  )
}

export function Dashboard() {
  const query = useDashboard()
  const data = query.data
  const density = useDashboardStore((state) => state.density)
  const selectedRecordId = useDashboardStore((state) => state.selectedRecordId)
  const setSourceOpen = useDashboardStore((state) => state.setSourceDrawerOpen)
  const setSettingsOpen = useDashboardStore((state) => state.setSettingsOpen)

  const recordsByCategory = useCallback(
    (...categories: string[]) =>
      data?.records.filter((record) => categories.includes(record.category)) ?? [],
    [data?.records],
  )
  const selected = data?.records.find((record) => record.id === selectedRecordId)
  const sourceState = data?.metadata.source_health ?? 'unavailable'
  const fullScreen = async () => {
    if (!document.fullscreenElement) await document.documentElement.requestFullscreen()
    else await document.exitFullscreen()
  }

  const utilityRecords = useMemo(
    () => recordsByCategory('power_outage_summary', 'stormwater_pump_asset'),
    [recordsByCategory],
  )

  if (query.isLoading && !data)
    return (
      <main className="loading-shell" aria-label="Loading emergency management dashboard">
        <Skeleton>
          <SkeletonItem />
          <SkeletonItem />
          <SkeletonItem />
        </Skeleton>
      </main>
    )

  return (
    <div className={`app-shell density-${density}`}>
      <header className="app-header">
        <div className="brand-lockup">
          <img src="/mbfd-logo.jpg" alt="Miami Beach Fire Department" />
          <div>
            <h1>Miami Beach Emergency Management Dashboard</h1>
            <p>
              Emergency Operations Center <i /> Common Operating Picture
            </p>
          </div>
        </div>
        <div className="header-operations">
          <div className="header-time">
            <Clock />
            <span>Last dashboard refresh: {localTime(data?.metadata.generated_at)}</span>
          </div>
          <StatusPill state={sourceState} />
          <Tooltip content="Dashboard data-source health" relationship="label">
            <Button
              className="header-icon-button"
              appearance="subtle"
              icon={<Database24Regular />}
              aria-label="Open dashboard data-source health"
              onClick={() => setSourceOpen(true)}
            />
          </Tooltip>
          <Tooltip content="Full-screen kiosk view" relationship="label">
            <Button
              className="header-icon-button fullscreen-button"
              appearance="subtle"
              icon={<ArrowMaximize24Regular />}
              aria-label="Toggle full-screen kiosk view"
              onClick={() => void fullScreen()}
            />
          </Tooltip>
          <Tooltip content="Dashboard settings" relationship="label">
            <Button
              className="header-icon-button"
              appearance="subtle"
              icon={<Settings24Regular />}
              aria-label="Open dashboard settings"
              onClick={() => setSettingsOpen(true)}
            />
          </Tooltip>
        </div>
      </header>

      {data?.metadata.stale && (
        <div className="degraded-banner" role="status">
          Showing cached information from {localTime(data.metadata.generated_at)}. Stale data is
          marked in each affected record.
        </div>
      )}
      {query.isError && !data && (
        <div className="degraded-banner error" role="alert">
          Source temporarily unavailable. No cached dashboard snapshot could be loaded.
        </div>
      )}

      <main id="main-content" className="dashboard-content">
        <section className="kpi-row" aria-label="Current operational indicators">
          {(data?.kpis ?? []).map((kpi) => (
            <button
              type="button"
              className={`kpi-tile kpi-${kpi.id}`}
              key={kpi.id}
              onClick={() => {
                const record = data?.records.find((item) => item.category === kpi.detail_category)
                if (record) useDashboardStore.getState().selectRecord(record.id)
              }}
            >
              <span>{kpi.label}</span>
              <strong>{kpi.unavailable ? 'Not available' : valueText(kpi.value)}</strong>
              <small>
                {kpi.source} · {kpi.updated_at ? localTime(kpi.updated_at) : 'Update unavailable'}
              </small>
            </button>
          ))}
        </section>

        <div className="dashboard-grid">
          <Suspense
            fallback={
              <section className="panel map-panel map-loading" aria-label="Loading operational map">
                Loading operational map…
              </section>
            }
          >
            <OperationalMap records={data?.records ?? []} />
          </Suspense>
          <WeatherCoastal records={data?.records ?? []} />
          <Panel title="PulsePoint Active Calls" subtitle="Advisory" className="pulsepoint-panel">
            <p className="required-disclaimer">PulsePoint advisory feed — not official CAD</p>
            <RecordList
              records={recordsByCategory('pulsepoint_call').filter(
                (record) => record.payload.state === 'active',
              )}
              empty="No current records returned by source"
            />
          </Panel>
          <Panel
            title="Road & Access Incidents"
            subtitle="Official public sources"
            className="traffic-panel"
          >
            <RecordList
              records={recordsByCategory('traffic_incident', 'lane_closure')}
              empty="No verified closure reported"
              limit={5}
            />
          </Panel>
          <Panel
            title="Official Public Notices"
            subtitle="Supplemental extraction"
            className="notices-panel"
          >
            <RecordList
              records={recordsByCategory('official_notice')}
              empty="No current records returned by source"
              limit={3}
            />
          </Panel>
          <Panel title="Shelter & Facility Information" className="facilities-panel">
            <div className="split-panel">
              <div>
                <h3>Open Shelter Records</h3>
                <RecordList
                  records={recordsByCategory('open_shelter')}
                  empty="No records returned — this does not mean no shelters exist"
                  limit={2}
                />
              </div>
              <div>
                <h3>Hospital & Hotel Locations</h3>
                <RecordList
                  records={recordsByCategory('hospital', 'hotel')}
                  empty="Status not available from current public sources"
                  limit={2}
                />
              </div>
            </div>
          </Panel>
          <Panel title="Power, Assets & Transit Awareness" className="utility-panel">
            <RecordList
              records={[...utilityRecords, ...recordsByCategory('transit')]}
              empty="Status not available from current public sources"
              limit={4}
            />
          </Panel>
          <Panel
            title="Dashboard Data-Source Health"
            className="health-panel"
            subtitle={data ? `${data.source_health.length} configured sources` : 'Not reported'}
          >
            <div className="health-summary">
              {(['healthy', 'delayed', 'stale', 'unavailable'] as const).map((state) => (
                <div key={state}>
                  <strong>
                    {data?.source_health.filter((source) => source.state === state).length ?? 0}
                  </strong>
                  <span>{state}</span>
                </div>
              ))}
              <Button appearance="subtle" onClick={() => setSourceOpen(true)}>
                Review every source
              </Button>
            </div>
          </Panel>
        </div>
      </main>
      <SourceDrawer health={data?.source_health ?? []} />
      <SettingsDrawer />
      <DetailDrawer record={selected} />
    </div>
  )
}
