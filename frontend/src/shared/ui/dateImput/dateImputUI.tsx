import type { FC } from 'react'
import { DateInput, type DateInputProps } from '@mantine/dates'

type Props = DateInputProps

export const DateInputUI: FC<Props> = ({
	label,
	placeholder = 'ММ/ДД/ГГГГ',
	required,
	size = 'lg',
	radius = 'md',
	style,
	...props
}) => {
	return (
		<DateInput
			label={label}
			placeholder={placeholder}
			required={required}
			size={size}
			radius={radius}
			style={{
				maxWidth: 262,
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
