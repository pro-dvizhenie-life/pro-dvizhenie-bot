import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './app/App.tsx'
import './app/style/index.css'
import '@mantine/core/styles.css'
import '@mantine/dates/styles.css'

import { BrowserRouter } from 'react-router-dom'
import { StoreProvider } from './providers/StoreProvider'
import { ErrorBoundary } from './providers/ErrorBoundary'

import { MantineProvider } from '@mantine/core'
import { DatesProvider } from '@mantine/dates'
import 'dayjs/locale/ru'

createRoot(document.getElementById('root')!).render(
	<StrictMode>
		<BrowserRouter>
			<StoreProvider>
				<ErrorBoundary>
					<MantineProvider>
						<DatesProvider settings={{ locale: 'ru', firstDayOfWeek: 1 }}>
							<App />
						</DatesProvider>
					</MantineProvider>
				</ErrorBoundary>
			</StoreProvider>
		</BrowserRouter>
	</StrictMode>
)