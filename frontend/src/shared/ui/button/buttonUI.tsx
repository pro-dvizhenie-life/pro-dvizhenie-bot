import type { FC } from 'react'
import { Button, type ButtonProps } from '@mantine/core'

type Props = ButtonProps

export const ButtonUI: FC<Props> = ({
	variant = 'filled',
	color = 'indigo',
	size = 'md',
	radius = 'xl',
	style,
	...props
}) => {
	return (
		<Button
			variant={variant}
			color={color}
			size={size}
			radius={radius}
			style={{
				width: 235,
				height: 48,
				...style,
			}}
			{...props}
		/>
	)
}
