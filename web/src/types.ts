import {z} from 'zod'

export const sourceHealthStateSchema = z.enum([
  'healthy',
  'delayed',
  'stale',
  'unavailable',
  'invalid_response',
  'scraper_layout_changed',
])

export const canonicalRecordSchema = z.object({
  id: z.string(),
  source_id: z.string(),
  source_name: z.string(),
  source_type: z.enum([
    'official_api',
    'official_gis',
    'official_feed',
    'pulsepoint_advisory',
    'official_web_scrape',
  ]),
  authority_level: z.enum(['authoritative', 'advisory', 'supplemental']),
  source_record_id: z.string(),
  source_url: z.string(),
  title: z.string(),
  category: z.string(),
  observed_at: z.string().nullable(),
  published_at: z.string().nullable(),
  retrieved_at: z.string(),
  expires_at: z.string().nullable(),
  stale: z.boolean(),
  stale_reason: z.string().nullable(),
  confidence: z.number(),
  geography: z.record(z.string(), z.unknown()),
  zip_scope: z.array(z.string()),
  raw_snapshot_hash: z.string(),
  schema_version: z.number(),
  payload: z.record(z.string(), z.unknown()),
})

export const responseMetadataSchema = z.object({
  generated_at: z.string(),
  source_observation_time: z.string().nullable(),
  data_age_seconds: z.number().nullable(),
  stale: z.boolean(),
  source_authority: z.array(z.enum(['authoritative', 'advisory', 'supplemental'])),
  source_health: sourceHealthStateSchema,
  last_successful_refresh: z.string().nullable(),
  empty_state: z.string().nullable(),
})

export const sourceHealthSchema = z.object({
  source_id: z.string(),
  source_name: z.string(),
  state: sourceHealthStateSchema,
  last_attempt: z.string().nullable(),
  last_success: z.string().nullable(),
  last_authoritative_observation: z.string().nullable(),
  current_data_age_seconds: z.number().nullable(),
  poll_interval_seconds: z.number(),
  consecutive_failures: z.number(),
  last_known_good: z.boolean(),
  authority_level: z.enum(['authoritative', 'advisory', 'supplemental']),
  circuit_breaker_state: z.enum(['closed', 'open', 'half_open']),
  schema_version: z.number(),
  message: z.string().nullable(),
})

export const dashboardSummarySchema = z.object({
  metadata: responseMetadataSchema,
  kpis: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      value: z.union([z.string(), z.number()]).nullable(),
      unavailable: z.boolean(),
      source: z.string(),
      updated_at: z.string().nullable(),
      detail_category: z.string(),
    }),
  ),
  records: z.array(canonicalRecordSchema),
  source_health: z.array(sourceHealthSchema),
})

export type CanonicalRecord = z.infer<typeof canonicalRecordSchema>
export type SourceHealth = z.infer<typeof sourceHealthSchema>
export type DashboardSummary = z.infer<typeof dashboardSummarySchema>
export type SourceHealthState = z.infer<typeof sourceHealthStateSchema>
