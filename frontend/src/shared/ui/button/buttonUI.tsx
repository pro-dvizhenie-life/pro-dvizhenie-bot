import type { FC } from 'react'
import { Button, type ButtonProps } from '@mantine/core'

type Props = ButtonProps

export const ButtonUI: FC<Props> = ({
	variant = 'filled',
	color = 'indigo',
	// size = 'md',
	radius = 'xl',
	style,
	...props
}) => {
	return (
		<Button
			variant={variant}
			color={color}
			size={'xl'}
			radius={radius}
			style={{
				// maxWidth: 235,
				width: '100%',
				height: 48,
				marginTop: 24,
				...style,
			}}
			{...props}
		/>
	)
}
