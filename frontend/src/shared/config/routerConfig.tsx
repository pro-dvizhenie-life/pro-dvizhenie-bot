import { MainPage } from 'src/pages/MainPage'
import { Dashboard } from 'src/pages/Dashboard'
import { NotFoundPage } from 'src/pages/NotFoundPage'

import type { RouteProps } from 'react-router'

export enum AppRoutes {
	MAIN = 'main',
  DASHBOARD = 'dashboard',

	NOT_FOUND = 'not_found',
}

export const RouterPath: Record<AppRoutes, string> = {
	[AppRoutes.MAIN]: '/',
  [AppRoutes.DASHBOARD]: '/dashboard',

	[AppRoutes.NOT_FOUND]: '*',
}

export const routerConfig: Record<AppRoutes, RouteProps> = {
	[AppRoutes.MAIN]: {
		path: RouterPath.main,
		element: <MainPage />,
	},
  [AppRoutes.DASHBOARD]: {
    path: RouterPath.dashboard,
    element: <Dashboard />,
  },

	[AppRoutes.NOT_FOUND]: {
		path: RouterPath.not_found,
		element: <NotFoundPage />,
	},
}
