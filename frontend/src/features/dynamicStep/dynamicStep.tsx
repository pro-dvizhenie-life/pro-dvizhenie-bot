import type { FC } from 'react'
import { Stack, Title, Text, Group, Textarea } from '@mantine/core'
import { useAppDispatch, useAppSelector } from '../../shared/hooks/redux'
import {
	selectStep,
	selectAnswers,
	selectQIndex,
	selectFieldErrors,
	setAnswer,
	advance,
} from '../../store/slices/stepsSlice'
import { ButtonUI } from '../../shared/ui/button/buttonUI'
import { RadioButtonUI } from '../../shared/ui/radioButton/radioButtonUI'
import { TextInputUI } from '../../shared/ui/textInput/textInputUI'
import type { Question } from '../../shared/lib/types'
import {
	isYesNo,
	isSelect,
	isText,
	isDate,
	isPhone,
	isEmailQ,
	isTextarea,
	getOptions,
	getQuestionText as getQText,
	NEED_CONSULTING_OPTIONS,
} from '../../features/dynamicStep/helpers'
import LogoUI from 'src/shared/ui/logo/logoUI'

export const DynamicStep: FC = () => {
	const dispatch = useAppDispatch()
	const step = useAppSelector(selectStep)
	const answers = useAppSelector(selectAnswers)
	const qIndex = useAppSelector(selectQIndex)
	const fieldErrors = useAppSelector(selectFieldErrors)

	const questions: Question[] = step?.questions ?? []
	const currentQ: Question | undefined = questions[qIndex]

	if (!step || !currentQ) return null

	const value = answers[currentQ.code]
	const setVal = (v: any) =>
		dispatch(setAnswer({ code: currentQ.code, value: v }))
	const next = () => {
		void dispatch(advance())
	}
	const answerAndNext = (v: any) => {
		setVal(v)
		void dispatch(advance())
	}

	const fieldError = fieldErrors[currentQ.code]

	return (
		<>
			<Stack style={{ position: 'fixed', top: 30, left: 30 }}>
				<LogoUI />
			</Stack>
			<Stack
				align='center'
				justify='center'
				gap='md'
				style={{ minHeight: '100vh' }}
			>
				<Title order={2}>{step.title}</Title>
				<Text size='xl'>{getQText(currentQ)}</Text>

				{currentQ.code === 'q_who_fills' && (
					<Stack gap='sm'>
						{getOptions(currentQ).map((opt) => (
							<RadioButtonUI
								key={opt.value}
								label={opt.label}
								value={opt.value}
								checked={value === opt.value}
								onChange={() => setVal(opt.value)}
							/>
						))}
						{fieldError && (
							<Text c='red' size='sm'>
								{fieldError}
							</Text>
						)}
						<ButtonUI onClick={next}>Продолжить</ButtonUI>
					</Stack>
				)}

				{isYesNo(currentQ) && currentQ.code !== 'q_who_fills' && (
					<Group gap='sm'>
						<ButtonUI onClick={() => answerAndNext(true)}>Да</ButtonUI>
						<ButtonUI onClick={() => answerAndNext(false)} color='gray'>
							Нет
						</ButtonUI>
					</Group>
				)}

				{isSelect(currentQ) && currentQ.code !== 'q_who_fills' && (
					<Stack gap='xs'>
						<Group gap='sm'>
							{getOptions(currentQ).map((opt) => (
								<ButtonUI
									key={String(opt.value)}
									onClick={() => answerAndNext(opt.value)}
								>
									{opt.label}
								</ButtonUI>
							))}
						</Group>
						{fieldError && (
							<Text c='red' size='sm'>
								{fieldError}
							</Text>
						)}
					</Stack>
				)}

				{isText(currentQ) && (
					<Stack gap='sm'>
						<TextInputUI
							label={getQText(currentQ)}
							value={String(value ?? '')}
							onChange={(e) => setVal(e.currentTarget.value)}
						/>
						{fieldError && (
							<Text c='red' size='sm'>
								{fieldError}
							</Text>
						)}
						<ButtonUI onClick={next}>Продолжить</ButtonUI>
					</Stack>
				)}

				{isPhone(currentQ) && (
					<Stack gap='sm'>
						<TextInputUI
							label={getQText(currentQ)}
							placeholder='+7XXXXXXXXXX'
							value={String(value ?? '')}
							onChange={(e) => setVal(e.currentTarget.value)}
							inputMode='tel'
						/>
						{fieldError && (
							<Text c='red' size='sm'>
								{fieldError}
							</Text>
						)}
						<ButtonUI onClick={next}>Продолжить</ButtonUI>
					</Stack>
				)}

				{isEmailQ(currentQ) && (
					<Stack gap='sm'>
						<TextInputUI
							label={getQText(currentQ)}
							placeholder='Введите email'
							type='email'
							value={String(value ?? '')}
							onChange={(e) => setVal(e.currentTarget.value)}
						/>
						{fieldError && (
							<Text c='red' size='sm'>
								{fieldError}
							</Text>
						)}
						<ButtonUI onClick={next}>Продолжить</ButtonUI>
					</Stack>
				)}

				{isDate(currentQ) && (
					<Stack gap='sm'>
						<TextInputUI
							label={getQText(currentQ)}
							placeholder='ГГГГ-ММ-ДД'
							value={String(value ?? '')}
							onChange={(e) => setVal(e.currentTarget.value)}
							inputMode='numeric'
						/>
						{fieldError && (
							<Text c='red' size='sm'>
								{fieldError}
							</Text>
						)}
						<ButtonUI onClick={next}>Продолжить</ButtonUI>
					</Stack>
				)}

				{currentQ.code === 'q_need_consulting' && (
					<Stack gap='xs'>
						<Group gap='sm'>
							{NEED_CONSULTING_OPTIONS.map((opt) => (
								<ButtonUI
									key={opt.value}
									onClick={() => answerAndNext(opt.value)}
								>
									{opt.label}
								</ButtonUI>
							))}
						</Group>
						{fieldError && (
							<Text c='red' size='sm'>
								{fieldError}
							</Text>
						)}
					</Stack>
				)}

				{isTextarea(currentQ) && currentQ.code !== 'q_need_consulting' && (
					<Stack gap='sm'>
						<Textarea
							label={getQText(currentQ)}
							autosize
							minRows={3}
							value={String(value ?? '')}
							onChange={(e) => setVal(e.currentTarget.value)}
						/>
						{fieldError && (
							<Text c='red' size='sm'>
								{fieldError}
							</Text>
						)}
						<ButtonUI onClick={next}>Продолжить</ButtonUI>
					</Stack>
				)}
			</Stack>
		</>
	)
}
