import type { FC } from 'react'
import { TextInput, type TextInputProps } from '@mantine/core'

type Props = TextInputProps

export const TextInputUI: FC<Props> = ({
	label,
	placeholder = 'Введите текст...',
	size = 'md',
	radius = 'md',
	style,
	...props
}) => {
	return (
		<TextInput
			label={label}
			placeholder={placeholder}
			size={size}
			radius={radius}
			style={{
				maxWidth: 371,
				width: '100%',
				height: 48,
				...style,
			}}
			styles={{
				input: { border: '1px solid var(--color-primary)' },
			}}
			{...props}
		/>
	)
}
