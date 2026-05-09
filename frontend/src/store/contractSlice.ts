import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { Contract, ProgressEvent } from '../types'

interface ContractState {
  contracts: Contract[]
  activeContractId: string | null
  progress: Record<string, ProgressEvent>
}

const initialState: ContractState = {
  contracts: [],
  activeContractId: null,
  progress: {},
}

const contractSlice = createSlice({
  name: 'contracts',
  initialState,
  reducers: {
    setContracts: (state, action: PayloadAction<Contract[]>) => {
      state.contracts = action.payload
    },
    setActiveContract: (state, action: PayloadAction<string>) => {
      state.activeContractId = action.payload
    },
    updateProgress: (state, action: PayloadAction<{ contractId: string; event: ProgressEvent }>) => {
      state.progress[action.payload.contractId] = action.payload.event
    },
  },
})

export const { setContracts, setActiveContract, updateProgress } = contractSlice.actions
export default contractSlice.reducer
