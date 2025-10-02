import { type FC, type ReactNode } from 'react'
import { Provider } from 'react-redux'
import { setupStore } from 'src/store/store'

const store = setupStore()

interface StoreProviderProps {
	children: ReactNode
}

export const StoreProvider: FC<StoreProviderProps> = ({ children }) => {
	return <Provider store={store}>{children}</Provider>
}