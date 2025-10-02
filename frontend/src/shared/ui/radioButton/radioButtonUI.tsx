import type { FC } from 'react'
import { Radio, type RadioProps } from '@mantine/core'

type Props = RadioProps

export const RadioButtonUI: FC<Props> = ({
	label,
	size = 'lg',
	style,
	...props
}) => {
	return (
		<Radio
			label={label}
			size={size}
			style={{
				maxWidth: 236,
				width: '100%',
				height: 32,
				...style,
			}}
			{...props}
		/>
	)
}
