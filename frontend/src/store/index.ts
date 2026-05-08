import { configureStore } from '@reduxjs/toolkit'
import authReducer from './authSlice'
import contractReducer from './contractSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    contracts: contractReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
