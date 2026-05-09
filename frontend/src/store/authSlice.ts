import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { User } from '../types'
import { authApi } from '../api/auth'

interface AuthState {
  user: User | null
  loading: boolean
}

const initialState: AuthState = { user: null, loading: false }

export const fetchMe = createAsyncThunk('auth/me', async () => {
  const res = await authApi.me()
  return res.data
})

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearUser: (state) => { state.user = null },
    setUser: (state, action: PayloadAction<User>) => { state.user = action.payload },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMe.pending, (state) => { state.loading = true })
      .addCase(fetchMe.fulfilled, (state, action) => {
        state.user = action.payload
        state.loading = false
      })
      .addCase(fetchMe.rejected, (state) => { state.loading = false })
  },
})

export const { clearUser, setUser } = authSlice.actions
export default authSlice.reducer
