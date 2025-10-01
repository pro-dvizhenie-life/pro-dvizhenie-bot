import type { FC } from 'react'
import { Textarea, type TextareaProps } from '@mantine/core'

type Props = TextareaProps

export const TextAreaUI: FC<Props> = ({
	label,
	placeholder = 'Введите текст...',
	size = 'lg',
	radius = 'md',
	style,
	...props
}) => {
	return (
		<Textarea
			label={label}
			placeholder={placeholder}
			size={size}
			radius={radius}
			style={{
				maxWidth: 778,
				width: '100%',
				minHeight: 112,
				...style,
			}}
			styles={{
				input: { border: '1px solid var(--color-primary)' },
			}}
			{...props}
		/>
	)
}
