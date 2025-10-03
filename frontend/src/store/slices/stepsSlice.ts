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
    qIndex: number
    fieldErrors: Record<string, string>
}

const initialState: StepsState = {
    step: null,
    answers: {},
    isLoading: false,
    error: null,
    isFinished: false,
    qIndex: 0,
    fieldErrors: {},
}

export const fetchStep = createAsyncThunk<Step, number>(
    'steps/fetchStep',
    async (stepId) => await fetchStepById(stepId)
)

const toYMD = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export const advance = createAsyncThunk<
    { progressed: true } | { progressed: false; nextStep: any | null },
    void,
    { state: RootState; rejectValue: any }
>('steps/advance', async (_: void, { getState, rejectWithValue }) => {
    const state = getState()
    const step = state.steps.step
    if (!step) return { progressed: true }

    const questions = step.questions ?? []
    const lastIndex = Math.max(0, questions.length - 1)
    const qIndex = state.steps.qIndex
    if (qIndex < lastIndex) return { progressed: true }

    const publicId = state.user.publicId
    if (!publicId) return rejectWithValue({ message: 'publicId отсутствует' })

    const payload: Answers = {}
    for (const q of questions) {
        let v: any = state.steps.answers[q.code]
        if ((q as any).type === 'date' && v instanceof Date) v = toYMD(v)
        if (v !== undefined) payload[q.code] = v
    }

    try {
        const resp = await sendStepAnswer(publicId, step.code, payload)
        return { progressed: false, nextStep: resp ?? null }
    } catch (err) {
        return rejectWithValue(err)
    }
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
            if (state.fieldErrors[action.payload.code]) {
                delete state.fieldErrors[action.payload.code]
            }
        },
        resetSteps: () => initialState,
        setStep: (state, action: PayloadAction<Step>) => {
            state.step = action.payload
            state.answers = {}
            state.isFinished = false
            state.error = null
            state.qIndex = 0
            state.fieldErrors = {}
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
                state.qIndex = 0
                state.fieldErrors = {}
            })
            .addCase(fetchStep.rejected, (state, action) => {
                state.isLoading = false
                state.error = action.error.message || 'Ошибка загрузки шага'
            })
            .addCase(advance.pending, (state) => {
                state.isLoading = true
                state.error = null
            })
            .addCase(advance.fulfilled, (state, action) => {
                state.isLoading = false
                if ('progressed' in action.payload && action.payload.progressed) {
                    const maxIdx = Math.max(0, (state.step?.questions?.length ?? 1) - 1)
                    state.qIndex = Math.min(maxIdx, state.qIndex + 1)
                    return
                }
                const next = (action.payload as any).nextStep
                if (next) {
                    const stepFromServer: Step = next.current_step ?? next
                    if (stepFromServer) {
                        state.step = stepFromServer
                        state.answers = {}
                        state.qIndex = 0
                        state.isFinished = false
                        state.fieldErrors = {}
                        return
                    }
                }
                state.isFinished = true
            })
            .addCase(advance.rejected, (state, action) => {
                state.isLoading = false
                if (action.payload) {
                    const p: any = action.payload
                    state.error = `HTTP ${p.status ?? ''} | ${p.url ?? ''}`
                    const fe: Record<string, string> = {}
                    const serverErrors = p?.server?.errors
                    if (Array.isArray(serverErrors)) {
                        for (const e of serverErrors) {
                            const code = e?.question ?? e?.question_code ?? e?.field ?? null
                            const msg = e?.message ?? e?.detail ?? (typeof e === 'string' ? e : JSON.stringify(e))
                            if (code && msg) fe[code] = msg
                        }
                    }
                    state.fieldErrors = fe
                } else {
                    state.error = action.error.message || 'Ошибка перехода по шагам'
                }
            })
    },
})

export const { setAnswer, resetSteps, setStep } = stepsSlice.actions
export default stepsSlice.reducer

export const selectStep        = (state: RootState) => state.steps.step
export const selectAnswers     = (state: RootState) => state.steps.answers
export const selectIsFinished  = (state: RootState) => state.steps.isFinished
export const selectIsLoading   = (state: RootState) => state.steps.isLoading
export const selectStepError   = (state: RootState) => state.steps.error
export const selectQIndex      = (state: RootState) => state.steps.qIndex
export const selectFieldErrors = (state: RootState) => state.steps.fieldErrors