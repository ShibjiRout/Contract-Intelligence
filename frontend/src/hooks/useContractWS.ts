import { useEffect, useRef } from 'react'
import { useDispatch } from 'react-redux'
import { updateProgress } from '../store/contractSlice'
import type { ProgressEvent } from '../types'

export function useContractWS(contractId: string | null) {
  const dispatch = useDispatch()
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!contractId) return
    const wsUrl = `${import.meta.env.VITE_WS_URL}/ws/contracts/${contractId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const data: ProgressEvent = JSON.parse(event.data)
      dispatch(updateProgress({ contractId, event: data }))
    }

    return () => ws.close()
  }, [contractId, dispatch])
}
