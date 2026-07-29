import {Button} from '@fluentui/react-components'
import {Pause20Regular, Play20Regular} from '@fluentui/react-icons'
import {radarStatusText} from './radar'

export function RadarControls({
  selectedFrame,
  playing,
  windowMinutes,
  opacity,
  unavailable,
  legendUrl,
  onTogglePlaying,
  onLatest,
  onWindowChange,
  onOpacityChange,
}: {
  selectedFrame: string | undefined
  playing: boolean
  windowMinutes: number
  opacity: number
  unavailable: boolean
  legendUrl: string | undefined
  onTogglePlaying: () => void
  onLatest: () => void
  onWindowChange: (minutes: number) => void
  onOpacityChange: (opacity: number) => void
}) {
  return (
    <div className="radar-controls" aria-label="Radar playback controls">
      <div className="radar-playback-actions">
        <Button
          size="small"
          appearance={playing ? 'primary' : 'secondary'}
          icon={playing ? <Pause20Regular /> : <Play20Regular />}
          aria-label={playing ? 'Pause radar animation' : 'Play radar animation'}
          onClick={onTogglePlaying}
        >
          {playing ? 'Pause' : 'Play'}
        </Button>
        <Button size="small" appearance="subtle" onClick={onLatest}>
          Latest
        </Button>
        <span className="radar-window" aria-label="Radar history window">
          {[30, 60, 120].map((minutes) => (
            <Button
              key={minutes}
              size="small"
              appearance={windowMinutes === minutes ? 'primary' : 'subtle'}
              onClick={() => onWindowChange(minutes)}
            >
              {minutes}
            </Button>
          ))}
          <small>min</small>
        </span>
      </div>
      <label className="radar-opacity">
        <span>Opacity</span>
        <input
          type="range"
          min="20"
          max="100"
          step="5"
          value={Math.round(opacity * 100)}
          onChange={(event) => onOpacityChange(Number(event.currentTarget.value) / 100)}
        />
      </label>
      <div className="radar-legend" aria-label="Radar reflectivity legend">
        {legendUrl ? (
          <img src={legendUrl} alt="NOAA MRMS reflectivity legend" />
        ) : (
          <>
            <span>Light</span>
            <i aria-hidden />
            <span>Heavy</span>
          </>
        )}
      </div>
      <p className={unavailable ? 'radar-status is-delayed' : 'radar-status'}>
        {radarStatusText(selectedFrame, new Date(), unavailable)}
      </p>
    </div>
  )
}
