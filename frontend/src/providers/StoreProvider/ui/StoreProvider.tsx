import { type FC, type ReactNode } from 'react'
import { Provider } from 'react-redux'
import { setupStore } from 'src/store/store'

interface StoreProviderProps {
	children: ReactNode
}

export const StoreProvider: FC<StoreProviderProps> = ({ children }) => {
	const store = setupStore()

	return <Provider store={store}>{children}</Provider>
}
