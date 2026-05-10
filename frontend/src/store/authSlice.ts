import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { User } from '../types'
import { authApi } from '../api/auth'

interface AuthState {
  user: User | null
  loading: boolean
  checked: boolean
}

const initialState: AuthState = { user: null, loading: false, checked: false }

export const fetchMe = createAsyncThunk('auth/me', async () => {
  const res = await authApi.me()
  return res.data
})

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearUser: (state) => {
      state.user = null
      state.checked = true
    },
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload
      state.checked = true
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMe.pending, (state) => { state.loading = true })
      .addCase(fetchMe.fulfilled, (state, action) => {
        state.user = action.payload
        state.loading = false
        state.checked = true
      })
      .addCase(fetchMe.rejected, (state) => {
        state.user = null
        state.loading = false
        state.checked = true
      })
  },
})

export const { clearUser, setUser } = authSlice.actions
export default authSlice.reducer
