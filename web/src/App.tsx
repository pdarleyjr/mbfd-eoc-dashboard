import {FluentProvider, webLightTheme} from '@fluentui/react-components'
import {Dashboard} from './components/Dashboard'

export function App() {
  return (
    <FluentProvider theme={webLightTheme}>
      <a className="skip-link" href="#main-content">
        Skip to dashboard content
      </a>
      <Dashboard />
    </FluentProvider>
  )
}
