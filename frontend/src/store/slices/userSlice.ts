import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { Step } from '../../shared/lib/types'
import { getPublicId } from '../../shared/api/userApi'

interface UserState {
    publicId: string
    currentStep: Step | null
    isLoading: boolean
    error: string | null
}

export const initPublicId = createAsyncThunk(
    'user/initPublicId',
    async () => {
        const { public_id, current_step } = await getPublicId()
        return { publicId: public_id, currentStep: current_step }
    }
)

const initialState: UserState = {
    publicId: '',
    currentStep: null,
    isLoading: false,
    error: null,
}

const userSlice = createSlice({
    name: 'user',
    initialState,
    reducers: {
        resetUser: () => initialState,
    },
    extraReducers: (builder) => {
        builder
            .addCase(initPublicId.pending, (state) => {
                state.isLoading = true
                state.error = null
            })
            .addCase(initPublicId.fulfilled, (state, action: PayloadAction<{ publicId: string; currentStep: Step }>) => {
                state.isLoading = false
                state.publicId = action.payload.publicId
                state.currentStep = action.payload.currentStep
            })
            .addCase(initPublicId.rejected, (state, action) => {
                state.isLoading = false
                state.error = action.error.message || 'Не удалось получить publicId'
            })
    },
})

export const { resetUser } = userSlice.actions
export default userSlice.reducer