import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './app/App.tsx'
import './app/style/index.css'
import '@mantine/core/styles.css'
import { BrowserRouter } from 'react-router'
import { StoreProvider } from './providers/StoreProvider/index.ts'
import { ErrorBoundary } from './providers/ErrorBoundary/index.ts'
import { MantineProvider } from '@mantine/core'

createRoot(document.getElementById('root')!).render(
	<StrictMode>
		<BrowserRouter>
			<StoreProvider>
				<ErrorBoundary>
					<MantineProvider>
						<App />
					</MantineProvider>
				</ErrorBoundary>
			</StoreProvider>
		</BrowserRouter>
	</StrictMode>
)
