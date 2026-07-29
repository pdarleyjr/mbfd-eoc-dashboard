import {expect, test, type Page} from '@playwright/test'

async function closeRecordDetails(page: Page) {
  const closeButton = page.getByRole('button', {name: 'Close record details'})
  await expect
    .poll(async () => {
      const box = await closeButton.boundingBox()
      const viewport = page.viewportSize()
      if (!box || !viewport) return false
      return (
        box.x >= 0 &&
        box.y >= 0 &&
        box.x + box.width <= viewport.width + 1 &&
        box.y + box.height <= viewport.height + 1
      )
    })
    .toBe(true)
  await closeButton.click()
  await expect(page.locator('.detail-drawer')).toBeHidden()
}

const now = '2026-07-27T14:00:00Z'
const record = {
  id: 'road-1',
  source_id: 'official-road',
  source_name: 'Official Road Source',
  source_type: 'official_gis',
  authority_level: 'authoritative',
  source_record_id: '1',
  source_url: 'https://example.gov/road',
  title: 'Verified lane restriction',
  category: 'lane_closure',
  observed_at: now,
  published_at: null,
  retrieved_at: now,
  expires_at: null,
  stale: true,
  stale_reason: 'Showing cached information after a failed refresh',
  confidence: 1,
  geography: {type: 'Point', coordinates: [-80.13, 25.79]},
  zip_scope: ['33139'],
  raw_snapshot_hash: 'a'.repeat(64),
  schema_version: 1,
  payload: {
    USER_status_desc: 'Active',
    USER_permit_number: 'ROW-2026-0042',
    USER_description:
      'Water-main extension work restricts the eastbound lane. Local access remains open.',
    USER_main_address_line_1: '1881 WASHINGTON AVE',
    USER_main_address_line_2: 'MIAMI BEACH, FL 33139',
    USER_issue_date: '2026-07-27T12:00:00Z',
    USER_expiration_date: '2026-07-31T21:00:00Z',
    text: `Miami Beach source text ${'with complete readable details '.repeat(40)}`,
  },
}

const pulseRecord = {
  ...record,
  id: 'pulse-1',
  source_id: 'pulsepoint-x1012',
  source_name: 'PulsePoint Miami Beach X1012',
  source_type: 'pulsepoint_advisory',
  authority_level: 'advisory',
  source_record_id: 'pulse-1',
  source_url: 'https://web.pulsepoint.org/?agency=X1012',
  title: 'Medical Emergency',
  category: 'pulsepoint_call',
  stale: false,
  stale_reason: null,
  geography: {type: 'Point', coordinates: [-80.12049, 25.83412]},
  payload: {
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
  },
}

const recentPulseRecord = {
  ...pulseRecord,
  id: 'pulse-2',
  source_record_id: 'pulse-2',
  title: 'Fire Alarm',
  geography: {},
  payload: {
    ...pulseRecord.payload,
    state: 'recent',
    call_type_code: 'FA',
    address: 'WASHINGTON AVE, MIAMI BEACH, FL',
    units: [],
  },
}

const laneLineRecord = {
  ...record,
  id: 'road-line',
  source_record_id: 'road-line',
  title: 'Washington Avenue lane restriction',
  stale: false,
  stale_reason: null,
  geography: {
    type: 'LineString',
    coordinates: [
      [-80.134, 25.785],
      [-80.133, 25.792],
    ],
  },
}

const floodRecord = {
  ...record,
  id: 'flood-ae',
  source_id: 'miami-beach-flood-ae',
  source_record_id: 'flood-ae',
  title: 'Preliminary FIRM AE flood zone',
  category: 'flood_zone',
  stale: false,
  stale_reason: null,
  geography: {
    type: 'Polygon',
    coordinates: [
      [
        [-80.137, 25.786],
        [-80.132, 25.786],
        [-80.132, 25.791],
        [-80.137, 25.791],
        [-80.137, 25.786],
      ],
    ],
  },
  payload: {zone: 'AE'},
}

const multiPointFacilityRecord = {
  ...record,
  id: 'facility-multipoint',
  source_id: 'official-facilities',
  source_name: 'Official Facilities Source',
  source_record_id: 'facility-multipoint',
  title: 'Hospital campus entrances',
  category: 'hospital',
  stale: false,
  stale_reason: null,
  geography: {
    type: 'MultiPoint',
    coordinates: [
      [-80.141, 25.812],
      [-80.14, 25.813],
    ],
  },
  payload: {},
}

const hotelFacilityRecord = {
  ...record,
  id: 'facility-hotel',
  source_id: 'official-hotels',
  source_name: 'Official Hotel Source',
  source_record_id: 'facility-hotel',
  title: 'Island House',
  category: 'hotel',
  stale: false,
  stale_reason: null,
  geography: {},
  payload: {},
}

const trafficCameraRecord = {
  ...record,
  id: 'traffic-camera-1385',
  source_id: 'fdem-fl511-traffic-cameras',
  source_name: 'FDEM / FL511 Traffic Cameras',
  source_record_id: '1385',
  title: 'I-395 East of Bridge Road',
  category: 'traffic_camera',
  stale: false,
  stale_reason: null,
  geography: {type: 'Point', coordinates: [-80.151245, 25.771976]},
  payload: {
    DESCRIPT: 'I-395 East of Bridge Road',
    COUNTY: 'Miami-Dade',
    HIGHWAY: 'I-395',
    DIRECTION: 'E',
    IMAGE: 'https://images-dis.divas.cloud/DGI/chan-256_h.jpg',
  },
}

const noticeRecord = {
  ...record,
  id: 'notice-1',
  source_id: 'miami-dade-emergency-activation',
  source_name: 'Miami-Dade Emergency Information',
  source_type: 'official_web_scrape',
  authority_level: 'supplemental',
  source_record_id: 'notice-1',
  title: 'Miami-Dade DEM monitors Atlantic storms',
  category: 'official_notice',
  stale: false,
  stale_reason: null,
  geography: {},
  payload: {
    text: 'Miami-Dade DEM is monitoring potential Atlantic storms. Officials will provide updates if systems threaten the county.',
  },
}

const powerRecord = {
  ...record,
  id: 'eia-demand',
  source_id: 'eia-fpl-demand',
  source_name: 'U.S. EIA-930 — FPL Demand',
  source_type: 'official_api',
  source_record_id: 'FPL:D:2026-07-27T10-04:00',
  title: 'FPL regional grid demand',
  category: 'power_grid_status',
  stale: false,
  stale_reason: null,
  geography: {},
  payload: {
    respondent: 'FPL',
    metric_type: 'D',
    metric_name: 'Demand',
    value: 23418,
    unit: 'megawatthours',
    geographic_scope: 'Florida Power & Light balancing authority',
    scope_note: 'Regional grid indicator; not a Miami Beach customer-outage count',
  },
}

const utilityAssetRecord = {
  ...record,
  id: 'stormwater-pump-5072',
  source_id: 'miami-beach-stormwater-pumps',
  source_name: 'Miami Beach Stormwater Pump Stations',
  source_record_id: 'STM_PMP_5072',
  title: 'STM_PMP_5072',
  category: 'stormwater_pump_asset',
  stale: false,
  stale_reason: null,
  geography: {},
  payload: {},
}

const summary = {
  metadata: {
    generated_at: now,
    source_observation_time: now,
    data_age_seconds: 120,
    stale: true,
    source_authority: ['authoritative'],
    source_health: 'stale',
    last_successful_refresh: now,
    empty_state: null,
  },
  kpis: [
    {
      id: 'pulsepoint',
      label: 'Active Calls',
      value: 1,
      unavailable: false,
      source: 'PulsePoint advisory',
      updated_at: now,
      detail_category: 'pulsepoint_call',
    },
    {
      id: 'roads',
      label: 'Road & Access Incidents',
      value: 2,
      unavailable: false,
      source: 'Official Road Source',
      updated_at: now,
      detail_category: 'lane_closure',
    },
    {
      id: 'alerts',
      label: 'Weather Alerts',
      value: 0,
      unavailable: false,
      source: 'National Weather Service',
      updated_at: now,
      detail_category: 'weather_alert',
    },
    {
      id: 'power',
      label: 'Power',
      value: '23,418 MWh',
      unavailable: false,
      source: 'EIA-930 · FPL regional; not local outage data',
      updated_at: now,
      detail_category: 'power_grid_status',
    },
    {
      id: 'shelters',
      label: 'Open Shelter Records',
      value: 0,
      unavailable: false,
      source: 'FEMA Open Shelters',
      updated_at: now,
      detail_category: 'open_shelter',
    },
    {
      id: 'sources',
      label: 'Critical Feeds',
      value: '6/6',
      unavailable: false,
      source: '1/1 all configured sources healthy',
      updated_at: now,
      detail_category: 'source_health',
    },
  ],
  records: [
    record,
    pulseRecord,
    recentPulseRecord,
    laneLineRecord,
    floodRecord,
    multiPointFacilityRecord,
    hotelFacilityRecord,
    trafficCameraRecord,
    noticeRecord,
    powerRecord,
    utilityAssetRecord,
  ],
  source_health: [
    {
      source_id: 'official-road',
      source_name: 'Official Road Source',
      state: 'stale',
      last_attempt: now,
      last_success: now,
      last_authoritative_observation: now,
      current_data_age_seconds: 120,
      poll_interval_seconds: 60,
      consecutive_failures: 1,
      last_known_good: true,
      authority_level: 'authoritative',
      circuit_breaker_state: 'closed',
      schema_version: 1,
      message: 'Source temporarily unavailable',
    },
  ],
  health_summary: {
    critical_healthy: 6,
    critical_total: 6,
    all_healthy: 0,
    all_total: 1,
    unavailable_critical: [],
  },
}

const radarResponse = {
  metadata: {
    generated_at: '2026-07-29T12:49:00Z',
    source_observation_time: '2026-07-29T12:48:14Z',
    data_age_seconds: 46,
    stale: false,
    source_authority: ['authoritative'],
    source_health: 'healthy',
    last_successful_refresh: '2026-07-29T12:49:00Z',
    empty_state: null,
  },
  records: [
    {
      ...record,
      id: 'radar-status',
      source_id: 'noaa-mrms-radar-status',
      source_name: 'NOAA nowCOAST MRMS Radar',
      source_record_id: 'conus_base_reflectivity_mosaic',
      source_url:
        'https://nowcoast.noaa.gov/geoserver/observations/weather_radar/wms?SERVICE=WMS&REQUEST=GetCapabilities',
      title: 'NOAA MRMS base reflectivity status',
      category: 'radar_status',
      observed_at: '2026-07-29T12:48:14Z',
      stale: false,
      stale_reason: null,
      geography: {},
      payload: {
        service_available: true,
        service_url: 'https://nowcoast.noaa.gov/geoserver/observations/weather_radar/wms',
        layer_name: 'conus_base_reflectivity_mosaic',
        legend_url:
          'https://nowcoast.noaa.gov/geoserver/observations/weather_radar/ows?service=WMS&request=GetLegendGraphic&format=image%2Fpng&layer=conus_base_reflectivity_mosaic',
        latest_frame_time: '2026-07-29T12:48:14Z',
        extent_start: '2026-07-29T11:36:12Z',
        extent_end: '2026-07-29T12:48:14Z',
        frame_times: [
          '2026-07-29T11:36:12Z',
          '2026-07-29T11:52:10Z',
          '2026-07-29T12:08:06Z',
          '2026-07-29T12:24:08Z',
          '2026-07-29T12:40:03Z',
          '2026-07-29T12:48:14Z',
        ],
        update_frequency_seconds: 240,
      },
    },
  ],
}

test.beforeEach(async ({page}) => {
  if (process.env.EOC_TEST_REAL_OSM !== '1') {
    await page.route('https://tile.openstreetmap.org/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: Buffer.from(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAEklEQVR42mNk+M9QzwAEYgH9eRZqGQAAAABJRU5ErkJggg==',
          'base64',
        ),
      })
    })
  }
  await page.route('**/api/v1/dashboard/summary', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(summary),
    })
  })
  await page.route('**/api/v1/radar/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(radarResponse),
    })
  })
  await page.route('https://nowcoast.noaa.gov/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'image/png',
      body: Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAEklEQVR42mNk+M9QzwAEYgH9eRZqGQAAAABJRU5ErkJggg==',
        'base64',
      ),
    })
  })
})

test('renders the keyless OpenStreetMap fallback and selects a mapped feature', async ({page}) => {
  const tileRequests: string[] = []
  const tileStatuses: number[] = []
  const missingMarkerAssets: string[] = []
  page.on('request', (request) => {
    if (request.url().startsWith('https://tile.openstreetmap.org/')) {
      tileRequests.push(request.url())
    }
  })
  page.on('response', (response) => {
    if (response.url().startsWith('https://tile.openstreetmap.org/')) {
      tileStatuses.push(response.status())
    }
    if (
      response.status() >= 400 &&
      /\/marker-(?:icon|shadow)(?:-[^/]+)?\.png$/.test(new URL(response.url()).pathname)
    ) {
      missingMarkerAssets.push(response.url())
    }
  })
  await page.goto('/')

  const map = page.getByRole('region', {name: 'Miami Beach operational map'})
  await expect(map).toBeVisible()
  await expect(map.getByRole('link', {name: /OpenStreetMap contributors/i})).toBeVisible()
  await expect(map.locator('img.leaflet-tile-loaded').first()).toBeVisible()
  await expect(map).toHaveAttribute('aria-busy', 'false', {timeout: 20_000})
  expect(tileRequests.length).toBeGreaterThan(0)
  expect(
    tileRequests.every((url) =>
      /^https:\/\/tile\.openstreetmap\.org\/\d+\/\d+\/\d+\.png$/.test(url),
    ),
  ).toBe(true)
  expect(tileStatuses).toHaveLength(tileRequests.length)
  expect(tileStatuses.every((status) => status === 200)).toBe(true)
  expect(missingMarkerAssets).toEqual([])
  if (process.env.EOC_TEST_REAL_OSM === '1') {
    await page.screenshot({path: 'test-results/real-osm-local.png'})
  }

  const mappedRoad = map.getByRole('button', {name: /Verified lane restriction/i})
  const markerBox = await mappedRoad.boundingBox()
  expect(markerBox?.width).toBeGreaterThanOrEqual(44)
  expect(markerBox?.height).toBeGreaterThanOrEqual(44)
  await mappedRoad.click()
  await expect(page.locator('.detail-drawer')).toBeVisible()
  await expect(page.getByRole('link', {name: 'Open official source'})).toBeVisible()
})

test('shows operational record content and synchronizes cards with map selection', async ({
  page,
}) => {
  await page.goto('/')

  const pulsePanel = page.locator('.pulsepoint-panel')
  const pulseCall = pulsePanel.getByRole('button', {name: /Medical Emergency/i})
  await expect(pulseCall).toBeVisible()
  await expect(pulseCall).toContainText('ME')
  await expect(pulseCall).toContainText('COLLINS AVE, MIAMI BEACH, FL')
  await expect(pulseCall).toContainText('CPT5')
  await expect(pulseCall).toContainText('On Scene')
  await expect(pulseCall).toContainText('+1')
  await expect(pulsePanel.getByText('No units reported')).toBeVisible()
  await expect(pulsePanel.getByText('Coordinates unavailable')).toBeVisible()
  await pulseCall.click()

  const detailDrawer = page.locator('.detail-drawer')
  await expect(detailDrawer.getByRole('heading', {name: 'Advisory units'})).toBeVisible()
  await expect(detailDrawer.getByText('Available on Radio')).toBeVisible()
  await expect(detailDrawer.getByText(/not authoritative CAD assignments/i)).toBeVisible()
  const selectedMarker = page.locator('.leaflet-record-marker.is-selected')
  await expect(selectedMarker).toBeVisible()
  await expect
    .poll(async () => {
      const markerBox = await selectedMarker.boundingBox()
      const mapBox = await page.locator('.leaflet-map').boundingBox()
      if (!markerBox || !mapBox) return Number.POSITIVE_INFINITY
      return Math.abs(markerBox.x + markerBox.width / 2 - (mapBox.x + mapBox.width / 2))
    })
    .toBeLessThan(60)
  await expect
    .poll(async () => {
      const markerBox = await selectedMarker.boundingBox()
      const mapBox = await page.locator('.leaflet-map').boundingBox()
      if (!markerBox || !mapBox) return Number.POSITIVE_INFINITY
      const markerAnchorY = markerBox.y + markerBox.height - 2
      return Math.abs(markerAnchorY - (mapBox.y + mapBox.height / 2))
    })
    .toBeLessThan(60)
  await closeRecordDetails(page)

  const roadPanel = page.locator('.traffic-panel')
  await expect(
    roadPanel.getByRole('button', {name: /1881 WASHINGTON AVE.*ROW-2026-0042/i}).first(),
  ).toContainText('Water-main extension work restricts the eastbound lane.')
  await expect(page.locator('.notices-panel')).toContainText(
    'Miami-Dade DEM is monitoring potential Atlantic storms.',
  )
  await expect(page.getByRole('button', {name: /Power.*23,418 MWh/i})).toBeVisible()

  const map = page.getByRole('region', {name: 'Miami Beach operational map'})
  const line = map.getByRole('button', {name: /Washington Avenue lane restriction/i})
  await line.focus()
  await line.press('Enter')
  await expect(detailDrawer).toBeVisible()
  await closeRecordDetails(page)

  await page.getByRole('button', {name: 'Layer'}).click({force: true})
  const floodLayerToggle = page.getByRole('checkbox', {name: 'Flood zones'})
  await floodLayerToggle.evaluate((element) => element.scrollIntoView({block: 'center'}))
  await floodLayerToggle.check({force: true})
  await page.getByRole('button', {name: 'Layer'}).click({force: true})
  const floodZone = map.getByRole('button', {name: /Preliminary FIRM AE flood zone/i})
  await floodZone.focus()
  await floodZone.press('Enter')
  await expect(detailDrawer).toBeVisible()
})

test('loads honest source states and supports drawers and layer controls', async ({
  page,
}, testInfo) => {
  await page.goto('/')

  await expect(
    page.getByRole('heading', {name: 'Miami Beach Emergency Management Dashboard'}),
  ).toBeVisible()
  await expect(page.getByAltText('Miami Beach Fire Department')).toBeVisible()
  await expect(page.getByRole('heading', {name: 'Active Calls'})).toBeVisible()
  await expect(page.getByText('PulsePoint advisory feed — not official CAD')).toHaveCount(0)
  await expect(page.getByText('Showing cached information', {exact: false})).toBeVisible()

  await page.getByRole('button', {name: 'Layer'}).click({force: true})
  const floodLayer = page.getByRole('checkbox', {name: 'Flood zones'})
  await expect(floodLayer).not.toBeChecked()
  const cameraLayer = page.getByRole('checkbox', {name: 'FL511 traffic cameras'})
  await expect(cameraLayer).not.toBeChecked()
  await floodLayer.evaluate((element) => element.scrollIntoView({block: 'center'}))
  await floodLayer.check({force: true})
  await cameraLayer.check({force: true})
  await expect(floodLayer).toBeChecked()
  await expect(cameraLayer).toBeChecked()
  await page.getByRole('button', {name: 'Layer'}).click({force: true})

  const trafficCamera = page.getByRole('button', {name: /I-395 East of Bridge Road/i})
  await trafficCamera.click()
  await expect(page.getByAltText('Live FL511 view: I-395 East of Bridge Road')).toBeVisible()
  await closeRecordDetails(page)

  await page
    .locator('.traffic-panel')
    .getByRole('button', {name: /1881 WASHINGTON AVE.*Water-main extension/i})
    .first()
    .click()
  await expect(page.getByRole('link', {name: 'Open official source'})).toBeVisible()
  await expect(page.getByRole('heading', {name: 'Source excerpt'})).toBeVisible()
  const drawer = page.locator('.detail-drawer')
  await expect(drawer).toBeVisible()
  await expect
    .poll(async () => {
      const box = await drawer.boundingBox()
      return (box?.x ?? 0) + (box?.width ?? 0)
    })
    .toBeLessThanOrEqual((page.viewportSize()?.width ?? 0) + 1)
  const drawerBox = await drawer.boundingBox()
  expect(drawerBox?.width).toBeGreaterThan(320)
  expect(drawerBox?.x).toBeGreaterThanOrEqual(0)
  const closeDetailsBox = await page
    .getByRole('button', {name: 'Close record details'})
    .boundingBox()
  expect(closeDetailsBox).not.toBeNull()
  expect(closeDetailsBox?.x).toBeGreaterThanOrEqual(0)
  expect((closeDetailsBox?.x ?? 0) + (closeDetailsBox?.width ?? 0)).toBeLessThanOrEqual(
    (page.viewportSize()?.width ?? 0) + 1,
  )
  await closeRecordDetails(page)

  await expect(page.getByRole('heading', {name: 'Dashboard Data-Source Health'})).toHaveCount(0)
  await expect(page.locator('.health-panel,.utility-panel,.facilities-panel')).toHaveCount(0)
  await expect(page.getByRole('button', {name: /Critical Feeds/})).toHaveCount(0)

  await page.getByRole('button', {name: /Power.*23,418 MWh/i}).click()
  await expect(page.getByRole('heading', {name: 'Power & Utility Awareness'})).toBeVisible()
  await expect(
    page.getByText(/documented open FPL customer-outage API is not currently/i),
  ).toBeVisible()
  await page.getByRole('button', {name: 'Close power details'}).click()
  await expect(page.getByRole('heading', {name: 'Power & Utility Awareness'})).toBeHidden()

  await page.getByRole('button', {name: /Open Shelter Records/i}).click()
  await expect(page.getByRole('heading', {name: 'Shelter Records'})).toBeVisible()
  await expect(page.getByText(/this does not mean no shelters exist/i)).toBeVisible()
  await page.getByRole('button', {name: 'Close shelter records'}).click()
  await expect(page.getByRole('heading', {name: 'Shelter Records'})).toBeHidden()

  await page.getByRole('button', {name: /Local Hospital.*Mount Sinai Medical Center/i}).click()
  await expect(page.getByRole('heading', {name: 'Mount Sinai Medical Center'})).toBeVisible()
  await expect(page.getByText('664 licensed beds')).toBeVisible()
  await expect(page.getByText(/8 red · 15 yellow · 20 green/i)).toBeVisible()
  await page.getByRole('button', {name: 'Close hospital details'}).click()
  await expect(page.getByRole('heading', {name: 'Mount Sinai Medical Center'})).toBeHidden()

  await page.getByRole('button', {name: 'Open dashboard health: Stale'}).click()
  await expect(page.getByRole('heading', {name: 'System Health & Critical Feeds'})).toBeVisible()
  await expect(page.getByLabel('System health summary')).toContainText('6/6 critical feeds')
  await expect(page.getByLabel('System health summary')).toContainText('0/1 all configured sources')
  await expect(page.getByText('Source temporarily unavailable')).toBeVisible()
  await expect(page.getByText('Retained')).toBeVisible()

  if (['desktop-1920', 'reduced-motion'].includes(testInfo.project.name)) {
    const dimensions = await page.evaluate(() => ({
      scrollHeight: document.documentElement.scrollHeight,
      clientHeight: document.documentElement.clientHeight,
    }))
    expect(dimensions.scrollHeight).toBeLessThanOrEqual(dimensions.clientHeight + 1)
  }
})

test('switches map modes, applies radar defaults, and starts animation only on request', async ({
  page,
}, testInfo) => {
  const radarRequests: string[] = []
  page.on('request', (request) => {
    if (request.url().startsWith('https://nowcoast.noaa.gov/') && request.url().includes('GetMap'))
      radarRequests.push(request.url())
  })
  await page.goto('/')

  await expect(page.getByRole('tab', {name: 'Operations'})).toHaveAttribute('aria-selected', 'true')
  expect(radarRequests).toHaveLength(0)

  await page.getByRole('tab', {name: 'Radar'}).click()
  await page.getByRole('button', {name: 'Layer'}).click()
  await expect(page.getByRole('checkbox', {name: 'MRMS radar'})).toBeChecked()
  await expect(page.getByRole('checkbox', {name: 'Weather alerts'})).toBeChecked()
  await expect(page.getByRole('checkbox', {name: 'Hospitals and hotels'})).not.toBeChecked()
  await expect(page.getByRole('checkbox', {name: 'Transit routes and stops'})).not.toBeChecked()
  await expect(page.getByRole('checkbox', {name: 'Stormwater pump assets'})).not.toBeChecked()
  await expect(page.getByRole('checkbox', {name: 'Evacuation zones'})).not.toBeChecked()
  await expect(page.getByText(/Radar delayed · Last frame/)).toBeVisible()
  await expect(page.getByRole('button', {name: 'Play radar animation'})).toBeVisible()
  await expect.poll(() => radarRequests.length).toBeGreaterThan(0)
  const requestedFrames = () =>
    new Set(
      radarRequests.map((request) => {
        const url = new URL(request)
        return url.searchParams.get('time') ?? url.searchParams.get('TIME')
      }),
    )
  expect(requestedFrames().size).toBe(1)
  await page.waitForTimeout(700)
  expect(requestedFrames().size).toBe(1)

  await page.getByRole('button', {name: 'Play radar animation'}).click()
  if (testInfo.project.name === 'reduced-motion') {
    await page.waitForTimeout(700)
    expect(requestedFrames().size).toBe(1)
  } else {
    await expect.poll(() => requestedFrames().size).toBeGreaterThan(1)
  }
})

test('collapses every over-map control into the Layer button', async ({page}) => {
  await page.goto('/')

  const layerButton = page.getByRole('button', {name: 'Layer'})
  await expect(layerButton).toBeVisible()
  await expect(layerButton).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByLabel('Map layers')).toHaveCount(0)
  await expect(page.getByLabel('Causeway quick focus')).toHaveCount(0)
  await expect(page.locator('.leaflet-control-zoom')).toBeHidden()

  await page.getByRole('tab', {name: 'Radar'}).click()
  await expect(page.getByRole('button', {name: 'Play radar animation'})).toHaveCount(0)

  await layerButton.click()
  await expect(layerButton).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByLabel('Map layers')).toBeVisible()
  await expect(page.getByLabel('Causeway quick focus')).toBeVisible()
  await expect(page.locator('.leaflet-control-zoom')).toBeVisible()
  await expect(page.getByRole('button', {name: 'Play radar animation'})).toBeVisible()
  const expandedOverlaps = await page.evaluate(() => {
    const controls = Array.from(
      document.querySelectorAll<HTMLElement>(
        '.layer-toggle-button,.layer-list,.radar-controls,.causeway-focus,.leaflet-control-zoom',
      ),
    )
      .filter((element) => getComputedStyle(element).display !== 'none')
      .map((element) => {
        const box = element.getBoundingClientRect()
        return {
          name: element.className,
          left: box.left,
          top: box.top,
          right: box.right,
          bottom: box.bottom,
        }
      })
    const overlaps: Array<[string, string]> = []
    for (let first = 0; first < controls.length; first += 1) {
      for (let second = first + 1; second < controls.length; second += 1) {
        const a = controls[first]
        const b = controls[second]
        const overlapX = Math.min(a.right, b.right) - Math.max(a.left, b.left)
        const overlapY = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top)
        if (overlapX > 2 && overlapY > 2) overlaps.push([a.name, b.name])
      }
    }
    return overlaps
  })
  expect(expandedOverlaps).toEqual([])

  await layerButton.click()
  await expect(layerButton).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByLabel('Map layers')).toHaveCount(0)
  await expect(page.getByLabel('Causeway quick focus')).toHaveCount(0)
  await expect(page.locator('.leaflet-control-zoom')).toBeHidden()
  await expect(page.getByRole('button', {name: 'Play radar animation'})).toHaveCount(0)
})

test('keeps primary controls keyboard reachable', async ({page}, testInfo) => {
  await page.goto('/')
  const sourceHealthButton = page.getByRole('button', {
    name: 'Open dashboard health: Stale',
  })
  const sourceHealthBox = await sourceHealthButton.boundingBox()

  expect(sourceHealthBox).not.toBeNull()
  if (!sourceHealthBox) throw new Error('Data-source health control has no layout box')
  expect(sourceHealthBox.width).toBeGreaterThanOrEqual(44)
  expect(sourceHealthBox.height).toBeGreaterThanOrEqual(44)

  if (testInfo.project.name === 'tablet-landscape' || testInfo.project.name === 'webkit-1440') {
    // Touch emulation does not consistently synthesize hardware-Tab navigation.
    // Programmatic focus still proves the skip link remains focusable for paired keyboards.
    await page.getByRole('link', {name: 'Skip to dashboard content'}).focus()
  } else {
    await page.keyboard.press('Tab')
  }
  const focused = page.locator(':focus')
  await expect(focused).toBeVisible()
  await expect(focused).toHaveAttribute('href', '#main-content')

  await page.getByRole('button', {name: 'Layer'}).click()
  for (const label of ['MacArthur', 'Julia Tuttle', 'Venetian', 'Reset map to Miami Beach']) {
    const quickFocusBox = await page.getByRole('button', {name: label}).boundingBox()
    expect(quickFocusBox, `${label} quick-focus control has no layout box`).not.toBeNull()
    expect(quickFocusBox?.width).toBeGreaterThanOrEqual(44)
    expect(quickFocusBox?.height).toBeGreaterThanOrEqual(44)
  }
})

test('does not overlap dashboard panels or overflow horizontally', async ({page}) => {
  await page.goto('/')
  await expect(page.locator('.weather-panel')).toBeVisible()
  const layout = await page.evaluate(() => {
    const panels = Array.from(document.querySelectorAll<HTMLElement>('.panel,.kpi-tile')).map(
      (element) => {
        const box = element.getBoundingClientRect()
        return {
          className: element.className,
          left: box.left,
          top: box.top,
          right: box.right,
          bottom: box.bottom,
        }
      },
    )
    const overlaps: Array<[string, string]> = []
    for (let first = 0; first < panels.length; first += 1) {
      for (let second = first + 1; second < panels.length; second += 1) {
        const a = panels[first]
        const b = panels[second]
        const overlapX = Math.min(a.right, b.right) - Math.max(a.left, b.left)
        const overlapY = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top)
        if (overlapX > 2 && overlapY > 2) overlaps.push([a.className, b.className])
      }
    }
    return {
      overlaps,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      weather: Array.from(
        document.querySelectorAll<HTMLElement>(
          '.weather-decision-grid,.weather-panel > .weather-alert,.tide-decision-strip',
        ),
      ).map((element) => {
        const box = element.getBoundingClientRect()
        return {top: box.top, bottom: box.bottom}
      }),
      weatherPanel: (() => {
        const box = document.querySelector<HTMLElement>('.weather-panel')?.getBoundingClientRect()
        return box ? {top: box.top, bottom: box.bottom} : null
      })(),
      mapPanel: (() => {
        const box = document.querySelector<HTMLElement>('.map-panel')?.getBoundingClientRect()
        return box ? {top: box.top, bottom: box.bottom} : null
      })(),
      weatherOverflow: Array.from(
        document.querySelectorAll<HTMLElement>(
          '.weather-decision-grid,.weather-panel > .weather-alert,.tide-decision-strip',
        ),
      ).flatMap((container) => {
        const bounds = container.getBoundingClientRect()
        return Array.from(container.querySelectorAll<HTMLElement>('*'))
          .filter((element) => {
            const box = element.getBoundingClientRect()
            return (
              box.width > 0 &&
              box.height > 0 &&
              (box.top < bounds.top - 1 || box.bottom > bounds.bottom + 1)
            )
          })
          .map((element) => element.className || element.tagName)
      }),
      kpiOverflow: Array.from(document.querySelectorAll<HTMLElement>('.kpi-tile')).flatMap(
        (container) => {
          const bounds = container.getBoundingClientRect()
          return Array.from(container.children)
            .filter((element) => {
              const box = element.getBoundingClientRect()
              return (
                box.width > 0 &&
                box.height > 0 &&
                (box.left < bounds.left - 1 ||
                  box.right > bounds.right + 1 ||
                  box.top < bounds.top - 1 ||
                  box.bottom > bounds.bottom + 1)
              )
            })
            .map((element) => element.className || element.tagName)
        },
      ),
    }
  })

  expect(layout.overlaps).toEqual([])
  expect(layout.kpiOverflow).toEqual([])
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.clientWidth + 1)
  if ((page.viewportSize()?.width ?? 0) >= 768) {
    expect(layout.mapPanel).not.toBeNull()
    expect(layout.weatherPanel).not.toBeNull()
    expect(
      Math.abs((layout.mapPanel?.top ?? 0) - (layout.weatherPanel?.top ?? 0)),
    ).toBeLessThanOrEqual(1)
    expect(
      Math.abs((layout.mapPanel?.bottom ?? 0) - (layout.weatherPanel?.bottom ?? 0)),
    ).toBeLessThanOrEqual(1)
  }
  if ((page.viewportSize()?.width ?? 0) >= 1400) {
    expect(layout.weatherPanel).not.toBeNull()
    expect(layout.weather).toHaveLength(3)
    expect(layout.weather[0].bottom).toBeLessThanOrEqual(layout.weather[1].top + 1)
    expect(layout.weather[1].bottom).toBeLessThanOrEqual(layout.weather[2].top + 1)
    expect(layout.weather[2].bottom).toBeLessThanOrEqual((layout.weatherPanel?.bottom ?? 0) + 1)
    expect(layout.weatherOverflow).toEqual([])
  }
})

test('contains the operational layout in one viewport without clipping record text', async ({
  page,
}) => {
  await page.goto('/')
  await expect(page.locator('.dashboard-content')).toBeVisible()
  const dimensions = await page.evaluate(() => ({
    scrollHeight: document.documentElement.scrollHeight,
    clientHeight: document.documentElement.clientHeight,
    contentScrollHeight:
      document.querySelector<HTMLElement>('.dashboard-content')?.scrollHeight ?? 0,
    contentClientHeight:
      document.querySelector<HTMLElement>('.dashboard-content')?.clientHeight ?? 0,
  }))
  const viewport = page.viewportSize()
  if ((viewport?.width ?? 0) >= 768) {
    expect(dimensions.scrollHeight).toBeLessThanOrEqual(dimensions.clientHeight + 1)
    expect(dimensions.contentScrollHeight).toBeLessThanOrEqual(dimensions.contentClientHeight + 1)
  } else {
    expect(dimensions.scrollHeight).toBeGreaterThanOrEqual(dimensions.clientHeight)
  }

  await expect(page.locator('.health-panel,.utility-panel,.facilities-panel')).toHaveCount(0)
  const gridBounds = await page.locator('.dashboard-grid').boundingBox()
  expect(gridBounds).not.toBeNull()
  for (const selector of ['.pulsepoint-panel', '.traffic-panel', '.notices-panel']) {
    const panelBounds = await page.locator(selector).boundingBox()
    expect(panelBounds, `${selector} has no layout box`).not.toBeNull()
    if (gridBounds && panelBounds) {
      expect(panelBounds.x).toBeGreaterThanOrEqual(gridBounds.x - 1)
      expect(panelBounds.y).toBeGreaterThanOrEqual(gridBounds.y - 1)
      expect(panelBounds.x + panelBounds.width).toBeLessThanOrEqual(
        gridBounds.x + gridBounds.width + 1,
      )
      expect(panelBounds.y + panelBounds.height).toBeLessThanOrEqual(
        gridBounds.y + gridBounds.height + 1,
      )
    }
  }

  const recordSummary = page
    .locator('.traffic-panel')
    .getByText('Water-main extension work restricts the eastbound lane.', {exact: true})
    .first()
  await recordSummary.scrollIntoViewIfNeeded()
  await expect(recordSummary).toBeVisible()
  const lineHeight = await recordSummary.evaluate((element) =>
    Number.parseFloat(getComputedStyle(element).lineHeight),
  )
  expect(lineHeight).toBeGreaterThanOrEqual(12)

  await page.locator('.traffic-panel').getByRole('button').first().click()
  const drawer = page.locator('.detail-drawer')
  await expect(drawer).toBeVisible()
  const drawerBox = await drawer.boundingBox()
  expect(drawerBox?.height).toBeLessThanOrEqual(
    page.viewportSize()?.height ?? Number.POSITIVE_INFINITY,
  )
  await expect(page.getByRole('button', {name: 'Close record details'})).toBeVisible()
})
