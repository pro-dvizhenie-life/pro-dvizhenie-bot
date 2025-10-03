import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { Step } from '../../shared/lib/types'
import { getPublicId } from '../../shared/api/userApi'
import type { RootState } from '../store'

interface UserState {
    publicId: string
    currentStep: Step | null
    isLoading: boolean
    error: string | null
}
export const selectPublicId = (state: RootState) => state.user.publicId

export const initPublicId = createAsyncThunk<
    { publicId: string; currentStep: Step },
    void,
    { state: RootState }
>('user/initPublicId', async (_, { getState }) => {
    const { user } = getState()
    if (user.publicId && user.currentStep) {
        return { publicId: user.publicId, currentStep: user.currentStep }
    }

    const { public_id, current_step } = await getPublicId()
    return { publicId: public_id, currentStep: current_step }
})

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