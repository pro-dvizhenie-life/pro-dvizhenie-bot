import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { RootState } from '../store'
import type { Step, Answers } from '../../shared/lib/types'
import { fetchStepById, sendStepAnswer } from '../../shared/api/stepsApi'

interface StepsState {
    step: Step | null
    answers: Answers
    isLoading: boolean
    error: string | null
    isFinished: boolean
}

const initialState: StepsState = {
    step: null,
    answers: {},
    isLoading: false,
    error: null,
    isFinished: false,
}

export const fetchStep = createAsyncThunk<Step, number>(
    'steps/fetchStep',
    async (stepId) => {
        return await fetchStepById(stepId)
    }
)

export const sendAnswer = createAsyncThunk<
    Step | null,
    { step: Step; answers: Answers; publicId: string }
>('steps/sendAnswer', async ({ step, answers, publicId }) => {
    return await sendStepAnswer(publicId, step.code, answers)
})

const stepsSlice = createSlice({
    name: 'steps',
    initialState,
    reducers: {
        setAnswer: (
            state,
            action: PayloadAction<{ code: string; value: string | number | boolean | null }>
        ) => {
            state.answers[action.payload.code] = action.payload.value
        },
        resetSteps: () => initialState,
        setStep: (state, action: PayloadAction<Step>) => {
            state.step = action.payload
            state.answers = {}
            state.isFinished = false
            state.error = null
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchStep.pending, (state) => {
                state.isLoading = true
                state.error = null
            })
            .addCase(fetchStep.fulfilled, (state, action) => {
                state.isLoading = false
                state.step = action.payload
            })
            .addCase(fetchStep.rejected, (state, action) => {
                state.isLoading = false
                state.error = action.error.message || 'Ошибка загрузки шага'
            })
            .addCase(sendAnswer.pending, (state) => {
                state.isLoading = true
                state.error = null
            })
            .addCase(sendAnswer.fulfilled, (state, action) => {
                state.isLoading = false
                state.step = action.payload
                state.answers = {}
                state.isFinished = action.payload === null
            })
            .addCase(sendAnswer.rejected, (state, action) => {
                state.isLoading = false
                state.error = action.error.message || 'Ошибка отправки ответа'
            })
    },
})

export const { setAnswer, resetSteps, setStep } = stepsSlice.actions
export default stepsSlice.reducer

export const selectStep = (state: RootState) => state.steps.step
export const selectAnswers = (state: RootState) => state.steps.answers
export const selectIsFinished = (state: RootState) => state.steps.isFinished
export const selectIsLoading = (state: RootState) => state.steps.isLoading
export const selectStepError = (state: RootState) => state.steps.error