import {QueryClient, QueryClientProvider} from '@tanstack/react-query'
import {StrictMode} from 'react'
import {createRoot} from 'react-dom/client'
import {App} from './App'
import './styles.css'

if ('serviceWorker' in navigator)
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register('/sw.js')
  })

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  },
})

const root = document.getElementById('root')
if (!root) throw new Error('Application root element is missing')

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
