import type { FC } from 'react'
import { PasswordInput, type PasswordInputProps } from '@mantine/core'

type Props = PasswordInputProps

export const PasswordInputUI: FC<Props> = ({
	label,
	placeholder = 'Введите пароль',
	required,
	size = 'lg',
	radius = 'md',
	style,
	...props
}) => {
	return (
		<PasswordInput
			label={label}
			placeholder={placeholder}
			required={required}
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
