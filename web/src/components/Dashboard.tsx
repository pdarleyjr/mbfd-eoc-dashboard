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
  Dismiss24Regular,
  Settings24Regular,
  ShieldError24Regular,
} from '@fluentui/react-icons'
import {lazy, Suspense, useCallback, useEffect, useMemo, useState} from 'react'
import {useDashboard} from '../hooks/useDashboard'
import {formatAge, localTime, recordTime, sourceStateLabel, valueText} from '../lib/format'
import {pulsePointCallLabel} from '../lib/pulsepoint'
import {useDashboardStore} from '../store/dashboardStore'
import type {CanonicalRecord, DashboardSummary} from '../types'
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

function payloadText(record: CanonicalRecord, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = record.payload[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
    if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  }
  return null
}

function conciseSentences(value: string | null, sentenceLimit = 1, maximum = 240): string | null {
  if (!value) return null
  const compact = value.replace(/\s+/g, ' ').trim()
  const matches = compact.match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? [compact]
  const candidate = matches.slice(0, sentenceLimit).join(' ').trim()
  if (candidate.length <= maximum) return candidate
  const shortened = candidate
    .slice(0, maximum)
    .replace(/\s+\S*$/, '')
    .replace(/[ ,;:-]+$/, '')
  return `${shortened || candidate.slice(0, maximum - 1)}…`
}

type AdvisoryUnit = {id: string; status: string | null; clearedAt: string | null}

function advisoryUnits(record: CanonicalRecord): AdvisoryUnit[] {
  const units = record.payload.units
  if (!Array.isArray(units)) return []
  return units.flatMap((unit) => {
    if (!unit || typeof unit !== 'object' || Array.isArray(unit)) return []
    const values = unit as Record<string, unknown>
    const id = typeof values.id === 'string' ? values.id.trim() : ''
    if (!id) return []
    return [
      {
        id,
        status: typeof values.status === 'string' && values.status.trim() ? values.status : null,
        clearedAt:
          typeof values.cleared_at === 'string' && values.cleared_at.trim()
            ? values.cleared_at
            : null,
      },
    ]
  })
}

function PulsePointList({records, limit = 5}: {records: CanonicalRecord[]; limit?: number}) {
  const selectRecord = useDashboardStore((state) => state.selectRecord)
  const ordered = [...records].sort((first, second) => {
    const firstActive = first.payload.state === 'active' ? 0 : 1
    const secondActive = second.payload.state === 'active' ? 0 : 1
    return firstActive - secondActive
  })
  if (!ordered.length)
    return (
      <div className="honest-empty">
        <ShieldError24Regular aria-hidden />
        <span>No current records returned by source</span>
      </div>
    )
  return (
    <ul className="operational-list pulsepoint-list" aria-label="PulsePoint advisory incidents">
      {ordered.slice(0, limit).map((record) => {
        const units = advisoryUnits(record)
        const active = record.payload.state === 'active'
        const hasCoordinates = record.geography.type === 'Point'
        const callTypeLabel = pulsePointCallLabel(record.payload.call_type_code)
        return (
          <li key={record.id}>
            <button type="button" onClick={() => selectRecord(record.id)}>
              <span className="operational-card-heading">
                <strong>{record.title}</strong>
                {callTypeLabel && <span className="call-code">{callTypeLabel}</span>}
                <span className={active ? 'state-tag state-active' : 'state-tag'}>
                  {active ? 'Active' : 'Recent'}
                </span>
                <span className={record.stale ? 'freshness-tag stale' : 'freshness-tag'}>
                  {record.stale ? 'Stale' : 'Live'}
                </span>
              </span>
              <span className="operational-location">
                {payloadText(record, 'address') ?? 'Address unavailable'}
              </span>
              <span className="unit-strip" aria-label="Advisory unit statuses">
                {units.length ? (
                  <>
                    {units.slice(0, 4).map((unit) => (
                      <span className="unit-chip" key={`${record.id}-${unit.id}`}>
                        <b>{unit.id}</b>
                        <small>{unit.status ?? 'Status not reported'}</small>
                      </span>
                    ))}
                    {units.length > 4 && <span className="unit-overflow">+{units.length - 4}</span>}
                  </>
                ) : (
                  <span className="no-units">No units reported</span>
                )}
              </span>
              <span className="operational-meta">
                <span>
                  {recordTime(record)} · {record.source_name}
                </span>
                {!hasCoordinates && <span>Coordinates unavailable</span>}
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

function roadLocation(record: CanonicalRecord): string {
  return (
    [
      payloadText(record, 'USER_main_address_line_1', 'address', 'LOCATION', 'location', 'HIGHWAY'),
      payloadText(record, 'USER_main_address_line_2'),
    ]
      .filter(Boolean)
      .join(', ') || record.title
  )
}

function RoadRecordList({records, limit = 5}: {records: CanonicalRecord[]; limit?: number}) {
  const selectRecord = useDashboardStore((state) => state.selectRecord)
  if (!records.length)
    return (
      <div className="honest-empty">
        <ShieldError24Regular aria-hidden />
        <span>No verified closure reported</span>
      </div>
    )
  return (
    <ul className="operational-list road-list" aria-label="Road and access records">
      {records.slice(0, limit).map((record) => {
        const summary = conciseSentences(
          payloadText(record, 'USER_description', 'DESCRIPT', 'REMARKS', 'text'),
        )
        const permit = payloadText(record, 'USER_permit_number')
        const status =
          payloadText(record, 'USER_status_desc', 'status', 'STATUS', 'SEVERITY') ??
          'Status reported by source'
        const start = payloadText(record, 'USER_issue_date', 'REPORTED')
        const end = payloadText(record, 'USER_expiration_date')
        return (
          <li key={record.id}>
            <button type="button" onClick={() => selectRecord(record.id)}>
              <span className="operational-card-heading">
                <strong>{roadLocation(record)}</strong>
                <span className="state-tag">{status}</span>
                <span className={`authority-mini authority-${record.authority_level}`}>
                  {record.authority_level}
                </span>
              </span>
              {summary && <span className="operational-summary">{summary}</span>}
              <span className="operational-meta">
                <span>
                  {permit ? `Permit ${permit} · ` : ''}
                  {start ? `Starts ${localTime(start)} · ` : ''}
                  {end ? `Ends ${localTime(end)}` : recordTime(record)}
                </span>
                <span>{record.stale ? 'Stale · View details' : 'Current · View details'}</span>
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

function NoticeRecordList({records, limit = 3}: {records: CanonicalRecord[]; limit?: number}) {
  const selectRecord = useDashboardStore((state) => state.selectRecord)
  if (!records.length)
    return (
      <div className="honest-empty">
        <ShieldError24Regular aria-hidden />
        <span>No current records returned by source</span>
      </div>
    )
  return (
    <ul className="operational-list notice-list" aria-label="Official public notices">
      {records.slice(0, limit).map((record) => (
        <li key={record.id}>
          <button type="button" onClick={() => selectRecord(record.id)}>
            <span className="operational-card-heading">
              <strong>{record.title}</strong>
              <span className={`authority-mini authority-${record.authority_level}`}>
                {record.authority_level}
              </span>
            </span>
            {conciseSentences(payloadText(record, 'text'), 2, 300) && (
              <span className="operational-summary">
                {conciseSentences(payloadText(record, 'text'), 2, 300)}
              </span>
            )}
            <span className="operational-meta">
              <span>
                {record.source_name} · Retrieved {recordTime(record)}
              </span>
              <span>View details</span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function powerMetricText(record: CanonicalRecord | undefined): string | null {
  if (!record) return null
  const value = record.payload.value
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  const unit = record.payload.unit === 'megawatthours' ? 'MWh' : valueText(record.payload.unit)
  return `${new Intl.NumberFormat('en-US', {maximumFractionDigits: 1}).format(value)} ${unit}`
}

function PowerGridStatus({records}: {records: CanonicalRecord[]}) {
  const selectRecord = useDashboardStore((state) => state.selectRecord)
  const demand = records.find((record) => record.payload.metric_type === 'D') ?? records[0]
  if (!demand) return null
  const renderedValue = powerMetricText(demand) ?? 'Value unavailable'
  return (
    <div className="power-grid-section">
      <button type="button" className="power-grid-card" onClick={() => selectRecord(demand.id)}>
        <span>
          <strong>{demand.title}</strong>
          <b>{renderedValue}</b>
        </span>
        <small>{payloadText(demand, 'geographic_scope')}</small>
        <p>{payloadText(demand, 'scope_note')}</p>
        <span className="operational-meta">EIA-930 · {recordTime(demand)} · View details</span>
      </button>
      <p>
        Regional grid demand is shown here. Local customer outages are available through FPL Power
        Tracker.
      </p>
      <a href="https://www.fpl.com/powertracker" target="_blank" rel="noreferrer">
        Open FPL Power Tracker
      </a>
    </div>
  )
}

function measurement(record: CanonicalRecord | undefined, key: string): number | null {
  const raw = record?.payload[key]
  if (typeof raw === 'number' && Number.isFinite(raw)) return raw
  if (typeof raw === 'string' && raw.trim() !== '') {
    const parsed = Number(raw)
    if (Number.isFinite(parsed)) return parsed
  }
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    const value = (raw as Record<string, unknown>).value
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string' && value.trim() !== '') {
      const parsed = Number(value)
      if (Number.isFinite(parsed)) return parsed
    }
  }
  return null
}

function fixed(value: number | null, digits = 0): string {
  return value === null ? 'Not available' : value.toFixed(digits)
}

function observedTime(record: CanonicalRecord): number {
  return Date.parse(record.observed_at ?? record.published_at ?? record.retrieved_at)
}

function WeatherCoastal({records}: {records: CanonicalRecord[]}) {
  const setMapMode = useDashboardStore((state) => state.setMapMode)
  const [renderedAt] = useState(() => Date.now())
  const forecasts = records
    .filter((record) => record.category === 'forecast' && record.payload.forecast_kind === 'hourly')
    .sort((first, second) => observedTime(first) - observedTime(second))
  const forecast = forecasts.find((record) => observedTime(record) >= renderedAt) ?? forecasts[0]
  const observation = records
    .filter((record) => record.category === 'weather_observation')
    .sort((first, second) => observedTime(second) - observedTime(first))[0]
  const alert = records.find((record) => record.category === 'weather_alert')
  const waterLevels = records
    .filter(
      (record) =>
        record.category === 'coastal_observation' && record.payload.product === 'water_level',
    )
    .sort((first, second) => observedTime(second) - observedTime(first))
  const observedWater = waterLevels[0]
  const previousWater = waterLevels[1]
  const predictedWater = records
    .filter(
      (record) =>
        record.category === 'coastal_observation' &&
        record.payload.product === 'predicted_water_level',
    )
    .sort(
      (first, second) =>
        Math.abs(observedTime(first) - (observedWater ? observedTime(observedWater) : renderedAt)) -
        Math.abs(observedTime(second) - (observedWater ? observedTime(observedWater) : renderedAt)),
    )[0]
  const tideRecords = records
    .filter(
      (record) =>
        record.category === 'coastal_observation' && record.payload.product === 'tide_predictions',
    )
    .sort((first, second) => observedTime(first) - observedTime(second))
  const highTides = tideRecords.filter((record) => record.payload.tide_type === 'H')
  const lowTides = tideRecords.filter((record) => record.payload.tide_type === 'L')
  const nextHigh = highTides.find((record) => observedTime(record) >= renderedAt) ?? highTides[0]
  const nextLow = lowTides.find((record) => observedTime(record) >= renderedAt) ?? lowTides[0]
  const hoursUntilHigh = nextHigh ? (observedTime(nextHigh) - renderedAt) / 3_600_000 : null

  const temperature = measurement(observation, 'temperature')
  const humidity = measurement(observation, 'relativeHumidity')
  const windSpeed = measurement(observation, 'windSpeed')
  const windGust = measurement(observation, 'windGust')
  const visibility = measurement(observation, 'visibility')
  const pressure = measurement(observation, 'barometricPressure')
  const precipitation = measurement(observation, 'precipitationLastHour')
  const observedLevel = measurement(observedWater, 'v')
  const priorLevel = measurement(previousWater, 'v')
  const predictedLevel = measurement(predictedWater, 'v')
  const anomaly =
    observedLevel !== null && predictedLevel !== null ? observedLevel - predictedLevel : null
  const trend =
    observedLevel === null || priorLevel === null
      ? 'Trend unavailable'
      : observedLevel > priorLevel
        ? 'Rising'
        : observedLevel < priorLevel
          ? 'Falling'
          : 'Steady'

  return (
    <Panel
      title="Weather & Coastal Conditions"
      subtitle="NWS · NOAA CO-OPS"
      className="weather-panel"
    >
      <div className="weather-decision-grid">
        <div className="weather-observed">
          <span>Observed now</span>
          <strong>
            {temperature === null ? 'Not available' : `${fixed((temperature * 9) / 5 + 32)}°F`}
          </strong>
          <small>
            {observation
              ? `${payloadText(observation, 'station_name', 'station_id') ?? 'NWS station'} · ${recordTime(observation)}`
              : 'Official observation unavailable'}
          </small>
          <p>Humidity {humidity === null ? '—' : `${fixed(humidity)}%`}</p>
          <p>
            Wind {windSpeed === null ? '—' : `${fixed(windSpeed * 0.621371)} mph`} · Gust{' '}
            {windGust === null ? '—' : `${fixed(windGust * 0.621371)} mph`}
            {measurement(observation, 'windDirection') === null
              ? ''
              : ` · ${fixed(measurement(observation, 'windDirection'))}°`}
          </p>
          <p>Visibility {visibility === null ? '—' : `${fixed(visibility / 1609.344)} mi`}</p>
          <p>Pressure {pressure === null ? '—' : `${fixed(pressure / 3386.389, 2)} inHg`}</p>
          <p>Rain {precipitation === null ? '—' : `${fixed(precipitation / 25.4, 2)} in`}</p>
        </div>
        <div className="weather-forecast">
          <span>Next-hour forecast</span>
          <strong>{forecast ? valueText(forecast.payload.shortForecast) : 'Not available'}</strong>
          <small>
            {forecast
              ? `${valueText(forecast.payload.temperature)}°${valueText(forecast.payload.temperatureUnit)} · ${recordTime(forecast)}`
              : 'Official forecast unavailable'}
          </small>
          <Button size="small" appearance="primary" onClick={() => setMapMode('radar')}>
            View Radar
          </Button>
        </div>
      </div>
      <div className={alert ? 'weather-alert active' : 'weather-alert'}>
        <span>Active NWS alert</span>
        <strong>{alert?.title ?? 'No current records returned by source'}</strong>
      </div>
      <div className="tide-decision-strip">
        <div>
          <span>Water level · MLLW</span>
          <strong>Observed {observedLevel === null ? '—' : `${fixed(observedLevel, 2)} m`}</strong>
          <small>
            Predicted {predictedLevel === null ? '—' : `${fixed(predictedLevel, 2)} m`} · Anomaly{' '}
            {anomaly === null ? '—' : `${anomaly >= 0 ? '+' : ''}${fixed(anomaly, 2)} m`} · {trend}{' '}
            · Station 8723214
          </small>
        </div>
        <div>
          <span>Next high</span>
          <strong>
            {nextHigh ? `${fixed(measurement(nextHigh, 'v'), 2)} m` : 'Not available'}
          </strong>
          <small>
            {nextHigh
              ? `${localTime(nextHigh.observed_at)}${
                  hoursUntilHigh !== null && hoursUntilHigh >= 0
                    ? ` · in ${fixed(hoursUntilHigh, 1)} hr`
                    : ''
                }`
              : 'CO-OPS prediction unavailable'}
          </small>
        </div>
        <div>
          <span>Next low</span>
          <strong>{nextLow ? `${fixed(measurement(nextLow, 'v'), 2)} m` : 'Not available'}</strong>
          <small>
            {nextLow ? localTime(nextLow.observed_at) : 'CO-OPS prediction unavailable'}
          </small>
        </div>
      </div>
    </Panel>
  )
}

function immediateAttention(
  records: CanonicalRecord[],
  unavailableCritical: string[],
): CanonicalRecord[] {
  const intersectsOperationalArea = (record: CanonicalRecord): boolean => {
    const points: Array<[number, number]> = []
    const collect = (value: unknown) => {
      if (Array.isArray(value)) {
        if (value.length >= 2 && typeof value[0] === 'number' && typeof value[1] === 'number') {
          points.push([value[0], value[1]])
          return
        }
        value.forEach(collect)
        return
      }
      if (value && typeof value === 'object')
        Object.values(value as Record<string, unknown>).forEach(collect)
    }
    collect(record.geography)
    if (!points.length) return false
    const longitudes = points.map(([longitude]) => longitude)
    const latitudes = points.map(([, latitude]) => latitude)
    return (
      Math.min(...longitudes) <= -80.1 &&
      Math.max(...longitudes) >= -80.2 &&
      Math.min(...latitudes) <= 25.89 &&
      Math.max(...latitudes) >= 25.74
    )
  }
  const highImpact = records.filter((record) => {
    const text = `${record.title} ${valueText(record.payload.event)} ${valueText(
      record.payload.severity,
    )}`.toLowerCase()
    if (
      record.category === 'weather_alert' &&
      (text.includes('severe') ||
        text.includes('extreme') ||
        text.includes('tornado') ||
        text.includes('flash flood'))
    )
      return true
    if (
      ['traffic_incident', 'lane_closure'].includes(record.category) &&
      /causeway|macarthur|julia tuttle|venetian/.test(text)
    )
      return true
    return record.category === 'tropical' && intersectsOperationalArea(record)
  })
  if (!unavailableCritical.length) return highImpact.slice(0, 3)
  return highImpact.slice(0, 2)
}

function SourceDrawer({
  health,
  summary,
}: {
  health: DashboardSummary['source_health']
  summary: DashboardSummary['health_summary'] | undefined
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
          System Health & Critical Feeds
        </DrawerHeaderTitle>
      </DrawerHeader>
      <DrawerBody>
        <div className="source-health-overview" aria-label="System health summary">
          <strong>
            {summary
              ? `${summary.critical_healthy}/${summary.critical_total} critical feeds`
              : 'Critical feeds not reported'}
          </strong>
          <strong>
            {summary
              ? `${summary.all_healthy}/${summary.all_total} all configured sources`
              : 'Configured sources not reported'}
          </strong>
          <span>
            {summary?.unavailable_critical.length
              ? `Needs attention: ${summary.unavailable_critical.join(', ')}`
              : 'No critical feed group is currently reported unavailable.'}
          </span>
        </div>
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

function PowerDrawer({
  open,
  onOpenChange,
  powerRecords,
  supportingRecords,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  powerRecords: CanonicalRecord[]
  supportingRecords: CanonicalRecord[]
}) {
  return (
    <Drawer
      type="overlay"
      position="end"
      size="large"
      open={open}
      onOpenChange={(_, data) => onOpenChange(data.open)}
    >
      <DrawerHeader>
        <DrawerHeaderTitle
          action={
            <Button
              appearance="subtle"
              icon={<Dismiss24Regular />}
              aria-label="Close power details"
              onClick={() => onOpenChange(false)}
            />
          }
        >
          Power & Utility Awareness
        </DrawerHeaderTitle>
      </DrawerHeader>
      <DrawerBody>
        <PowerGridStatus records={powerRecords} />
        <section className="drawer-section" aria-labelledby="local-outage-heading">
          <h3 id="local-outage-heading">Local FPL customer outages</h3>
          <p>
            A documented open FPL customer-outage API is not currently available to this dashboard.
            The official FPL Power Tracker remains the authoritative local outage view.
          </p>
          {powerRecords.length === 0 && (
            <a
              href="https://www.fpl.com/powertracker"
              target="_blank"
              rel="noreferrer"
              className="source-link"
            >
              Open FPL Power Tracker
            </a>
          )}
        </section>
        <section className="drawer-section" aria-labelledby="supporting-utility-heading">
          <h3 id="supporting-utility-heading">Assets and transit awareness</h3>
          <RecordList
            records={supportingRecords}
            empty="No current stormwater-asset or transit records were returned."
            limit={12}
          />
        </section>
      </DrawerBody>
    </Drawer>
  )
}

function ShelterDrawer({
  open,
  onOpenChange,
  records,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  records: CanonicalRecord[]
}) {
  return (
    <Drawer
      type="overlay"
      position="end"
      size="large"
      open={open}
      onOpenChange={(_, data) => onOpenChange(data.open)}
    >
      <DrawerHeader>
        <DrawerHeaderTitle
          action={
            <Button
              appearance="subtle"
              icon={<Dismiss24Regular />}
              aria-label="Close shelter records"
              onClick={() => onOpenChange(false)}
            />
          }
        >
          Shelter Records
        </DrawerHeaderTitle>
      </DrawerHeader>
      <DrawerBody>
        <p className="drawer-intro">
          Open FEMA shelter records and Miami-Dade evacuation-center inventory for the operational
          area.
        </p>
        <RecordList
          records={records}
          empty="No open shelter record was returned; this does not mean no shelters exist."
          limit={20}
        />
      </DrawerBody>
    </Drawer>
  )
}

function HospitalDrawer({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Drawer
      type="overlay"
      position="end"
      size="large"
      open={open}
      onOpenChange={(_, data) => onOpenChange(data.open)}
    >
      <DrawerHeader>
        <DrawerHeaderTitle
          action={
            <Button
              appearance="subtle"
              icon={<Dismiss24Regular />}
              aria-label="Close hospital details"
              onClick={() => onOpenChange(false)}
            />
          }
        >
          Mount Sinai Medical Center
        </DrawerHeaderTitle>
      </DrawerHeader>
      <DrawerBody>
        <div className="hospital-identity">
          <strong>4300 Alton Road, Miami Beach, FL 33140</strong>
          <span>Emergency Center open 24 hours, seven days a week</span>
          <span>Main 305-674-2121 · Emergency Room 305-674-2200</span>
        </div>
        <dl className="hospital-spec-grid">
          <div>
            <dt>Licensed capacity</dt>
            <dd>664 licensed beds</dd>
          </div>
          <div>
            <dt>Emergency department</dt>
            <dd>Only emergency department in Miami Beach · 56 treatment rooms</dd>
          </div>
          <div>
            <dt>General services</dt>
            <dd>Adult · pediatric · behavioral health</dd>
          </div>
          <div>
            <dt>Obstetrics</dt>
            <dd>General and high-risk obstetrics after 20 weeks</dd>
          </div>
          <div>
            <dt>Stroke</dt>
            <dd>Comprehensive Stroke Center</dd>
          </div>
          <div>
            <dt>Cardiac</dt>
            <dd>STEMI Center</dd>
          </div>
          <div>
            <dt>Special capabilities</dt>
            <dd>HAZMAT and radiological capable · heliport</dd>
          </div>
          <div>
            <dt>Mass-casualty capacity</dt>
            <dd>MCI capacity: 8 red · 15 yellow · 20 green</dd>
          </div>
          <div>
            <dt>Trauma center</dt>
            <dd>Not listed as provided in the Miami-Dade facilities table</dd>
          </div>
        </dl>
        <div className="reference-links" aria-label="Mount Sinai specification sources">
          <a
            href="https://mdsceh.miamidade.gov/mobi/moms/mdfr_moms_03092026.pdf"
            target="_blank"
            rel="noreferrer"
          >
            Miami-Dade facility capabilities
          </a>
          <a href="https://www.msmc.com/location/miami-beach/" target="_blank" rel="noreferrer">
            Mount Sinai Miami Beach
          </a>
          <a
            href="https://quality.healthfinder.fl.gov/Facility-Provider/Profile/?LID=9855"
            target="_blank"
            rel="noreferrer"
          >
            Florida licensed-facility profile
          </a>
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
  const trafficCameraImage =
    record?.category === 'traffic_camera' ? payloadText(record, 'IMAGE') : null
  const units = record ? advisoryUnits(record) : []
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
            {trafficCameraImage?.startsWith('https://') && (
              <figure className="traffic-camera-preview">
                <img src={trafficCameraImage} alt={`Live FL511 view: ${record.title}`} />
                <figcaption>
                  FL511 camera image · dashboard record retrieved {localTime(record.retrieved_at)}
                </figcaption>
              </figure>
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
            {units.length > 0 && (
              <section className="payload-array-section" aria-labelledby="advisory-units-heading">
                <h3 id="advisory-units-heading">Advisory units</h3>
                <p>
                  Unit identities and statuses are external advisory data, not authoritative CAD
                  assignments.
                </p>
                <ul>
                  {units.map((unit) => (
                    <li key={`${record.id}-${unit.id}`}>
                      <strong>{unit.id}</strong>
                      <span>{unit.status ?? 'Status not reported'}</span>
                      {unit.clearedAt && <small>Cleared {localTime(unit.clearedAt)}</small>}
                    </li>
                  ))}
                </ul>
              </section>
            )}
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
  const [overviewDrawer, setOverviewDrawer] = useState<'power' | 'shelters' | 'hospital' | null>(
    null,
  )
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

  const powerGridRecords = useMemo(
    () => recordsByCategory('power_grid_status'),
    [recordsByCategory],
  )
  const supportingUtilityRecords = useMemo(
    () => [...recordsByCategory('stormwater_pump_asset'), ...recordsByCategory('transit')],
    [recordsByCategory],
  )
  const shelterRecords = useMemo(
    () => recordsByCategory('open_shelter', 'evacuation_center'),
    [recordsByCategory],
  )
  const topKpis = useMemo(() => {
    const operational = (data?.kpis ?? [])
      .filter((kpi) => kpi.id !== 'sources')
      .map((kpi) => (kpi.id === 'power' ? {...kpi, label: 'Power'} : kpi))
    const demand =
      powerGridRecords.find((record) => record.payload.metric_type === 'D') ?? powerGridRecords[0]
    if (!operational.some((kpi) => kpi.id === 'power')) {
      operational.push({
        id: 'power',
        label: 'Power',
        value: powerMetricText(demand),
        unavailable: powerMetricText(demand) === null,
        source: 'EIA-930 · FPL regional; not local outage data',
        updated_at: demand?.observed_at ?? demand?.retrieved_at ?? null,
        detail_category: 'power_grid_status',
      })
    }
    return [
      ...operational,
      {
        id: 'hospital',
        label: 'Local Hospital',
        value: 'Mount Sinai Medical Center',
        unavailable: false,
        source: 'Miami-Dade EMS facility profile',
        updated_at: null,
        detail_category: 'hospital',
      },
    ]
  }, [data?.kpis, powerGridRecords])
  const unavailableCritical = useMemo(
    () => data?.health_summary.unavailable_critical ?? [],
    [data?.health_summary.unavailable_critical],
  )
  const attentionRecords = useMemo(
    () => immediateAttention(data?.records ?? [], unavailableCritical),
    [data?.records, unavailableCritical],
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
          <StatusPill
            state={sourceState}
            ariaLabel={`Open dashboard health: ${sourceStateLabel(sourceState)}`}
            onClick={() => setSourceOpen(true)}
          />
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
          {topKpis.map((kpi) => (
            <button
              type="button"
              className={`kpi-tile kpi-${kpi.id}`}
              key={kpi.id}
              onClick={() => {
                if (kpi.id === 'power') {
                  setOverviewDrawer('power')
                  return
                }
                if (kpi.id === 'shelters') {
                  setOverviewDrawer('shelters')
                  return
                }
                if (kpi.id === 'hospital') {
                  setOverviewDrawer('hospital')
                  return
                }
                const record = data?.records.find((item) => item.category === kpi.detail_category)
                if (record) useDashboardStore.getState().selectRecord(record.id)
              }}
            >
              <span>{kpi.label}</span>
              <strong>{kpi.unavailable ? 'Not available' : valueText(kpi.value)}</strong>
              <small>
                {kpi.source}
                {kpi.updated_at ? ` · ${localTime(kpi.updated_at)}` : ''}
              </small>
            </button>
          ))}
        </section>

        {(attentionRecords.length > 0 || unavailableCritical.length > 0) && (
          <section className="immediate-attention" aria-label="Immediate Attention">
            <strong>Immediate Attention</strong>
            <div>
              {attentionRecords.map((record) => (
                <button
                  type="button"
                  key={record.id}
                  onClick={() => useDashboardStore.getState().selectRecord(record.id)}
                >
                  {record.title}
                </button>
              ))}
              {unavailableCritical.map((source) => (
                <span key={source}>{source} source is unavailable or delayed</span>
              ))}
            </div>
          </section>
        )}

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
          <Panel title="Active Calls" subtitle="Advisory" className="pulsepoint-panel">
            <PulsePointList records={recordsByCategory('pulsepoint_call')} />
          </Panel>
          <Panel
            title="Road & Access Incidents"
            subtitle="Official public sources"
            className="traffic-panel"
          >
            <RoadRecordList records={recordsByCategory('traffic_incident', 'lane_closure')} />
          </Panel>
          <Panel
            title="Official Public Notices"
            subtitle="Supplemental extraction"
            className="notices-panel"
          >
            <NoticeRecordList records={recordsByCategory('official_notice')} />
          </Panel>
        </div>
      </main>
      <SourceDrawer health={data?.source_health ?? []} summary={data?.health_summary} />
      <PowerDrawer
        open={overviewDrawer === 'power'}
        onOpenChange={(open) => setOverviewDrawer(open ? 'power' : null)}
        powerRecords={powerGridRecords}
        supportingRecords={supportingUtilityRecords}
      />
      <ShelterDrawer
        open={overviewDrawer === 'shelters'}
        onOpenChange={(open) => setOverviewDrawer(open ? 'shelters' : null)}
        records={shelterRecords}
      />
      <HospitalDrawer
        open={overviewDrawer === 'hospital'}
        onOpenChange={(open) => setOverviewDrawer(open ? 'hospital' : null)}
      />
      <SettingsDrawer />
      <DetailDrawer record={selected} />
    </div>
  )
}
