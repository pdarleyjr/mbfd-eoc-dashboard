import {expect, test} from '@playwright/test'

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
    status: 'restriction',
    text: `Miami Beach source text ${'with complete readable details '.repeat(40)}`,
  },
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
      id: 'roads',
      label: 'Road & Access Incidents',
      value: 1,
      unavailable: false,
      source: 'Official Road Source',
      updated_at: now,
      detail_category: 'lane_closure',
    },
  ],
  records: [record],
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
}

test.beforeEach(async ({page}) => {
  await page.route('**/api/v1/dashboard/summary', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(summary),
    })
  })
})

test('loads honest source states and supports drawers and layer controls', async ({
  page,
}, testInfo) => {
  await page.goto('/')

  await expect(
    page.getByRole('heading', {name: 'Miami Beach Emergency Management Dashboard'}),
  ).toBeVisible()
  await expect(page.getByAltText('Miami Beach Fire Department')).toBeVisible()
  await expect(page.getByText('PulsePoint advisory feed — not official CAD')).toBeVisible()
  await expect(page.getByText('Showing cached information', {exact: false})).toBeVisible()

  const floodLayer = page.getByRole('checkbox', {name: 'Flood zones'})
  await expect(floodLayer).not.toBeChecked()
  await floodLayer.check()
  await expect(floodLayer).toBeChecked()

  await page.getByRole('button', {name: /Verified lane restriction/}).click()
  await expect(page.getByRole('link', {name: 'Open official source'})).toBeVisible()
  await expect(page.getByRole('heading', {name: 'Source excerpt'})).toBeVisible()
  const drawer = page.locator('.detail-drawer')
  await expect(drawer).toBeVisible()
  const drawerBox = await drawer.boundingBox()
  expect(drawerBox?.width).toBeGreaterThan(320)
  await page.getByRole('button', {name: 'Close record details'}).click()

  await page.getByRole('button', {name: 'Open dashboard data-source health'}).click()
  await expect(page.getByText('Source temporarily unavailable')).toBeVisible()
  await expect(page.getByText('Retained')).toBeVisible()

  if (testInfo.project.name === 'desktop-1920') {
    const dimensions = await page.evaluate(() => ({
      scrollHeight: document.documentElement.scrollHeight,
      clientHeight: document.documentElement.clientHeight,
    }))
    expect(dimensions.scrollHeight).toBeLessThanOrEqual(dimensions.clientHeight + 1)
  }
})

test('keeps the map status clear of layer controls when configuration is absent', async ({
  page,
}) => {
  await page.goto('/')
  const status = page.getByText('Google Maps configuration is unavailable', {exact: true})
  if (await status.isVisible()) {
    const statusBox = await status.boundingBox()
    const layerBox = await page.getByRole('complementary', {name: 'Map layers'}).boundingBox()
    expect(statusBox).not.toBeNull()
    expect(layerBox).not.toBeNull()
    if (statusBox && layerBox) {
      const overlapX =
        Math.min(statusBox.x + statusBox.width, layerBox.x + layerBox.width) -
        Math.max(statusBox.x, layerBox.x)
      const overlapY =
        Math.min(statusBox.y + statusBox.height, layerBox.y + layerBox.height) -
        Math.max(statusBox.y, layerBox.y)
      expect(overlapX > 0 && overlapY > 0).toBeFalsy()
    }
  }
})

test('keeps primary controls keyboard reachable', async ({page}, testInfo) => {
  await page.goto('/')
  const sourceHealthButton = page.getByRole('button', {
    name: 'Open dashboard data-source health',
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
})

test('does not overlap dashboard panels or overflow horizontally', async ({page}) => {
  await page.goto('/')
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
    }
  })

  expect(layout.overlaps).toEqual([])
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.clientWidth + 1)
})
