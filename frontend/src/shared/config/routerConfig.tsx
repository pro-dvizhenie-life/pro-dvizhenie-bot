import { MainPage } from 'src/pages/MainPage'
import { Dashboard } from 'src/pages/Dashboard'
import { NotFoundPage } from 'src/pages/NotFoundPage'
import { StepPage } from 'src/pages/application/stepPage'

import type { RouteProps } from 'react-router'

export enum AppRoutes {
	MAIN = 'main',
  DASHBOARD = 'dashboard',
	APPLICATION = 'application',
	NOT_FOUND = 'not_found',
}

export const RouterPath: Record<AppRoutes, string> = {
	[AppRoutes.MAIN]: '/',
  [AppRoutes.DASHBOARD]: '/dashboard',
	[AppRoutes.APPLICATION]: '/application',

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

	[AppRoutes.APPLICATION]: {
		path: RouterPath.application,
		element: <StepPage />,
	},

	[AppRoutes.NOT_FOUND]: {
		path: RouterPath.not_found,
		element: <NotFoundPage />,
	},
}
