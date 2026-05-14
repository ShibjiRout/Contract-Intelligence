import { useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import type { Clause } from '../../types'
import ClauseCard from './ClauseCard'

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface Props {
  contractId: string
  pdfUrl: string | null
  clauses: Clause[]
  onClauseUpdated?: () => void
}

export default function ContractViewer({ pdfUrl, clauses, onClauseUpdated }: Props) {
  const [numPages, setNumPages] = useState<number>(0)
  const [pdfError, setPdfError] = useState(false)

  return (
    <div className="flex h-full gap-4">
      {/* Left: PDF Viewer */}
      <div className="w-2/5 overflow-y-auto premium-panel bg-slate-50/80">
        {!pdfUrl ? (
          <div className="flex items-center justify-center h-full text-sm text-slate-500 gap-2">
            <div className="w-5 h-5 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
            <span>Loading PDF…</span>
          </div>
        ) : pdfError ? (
          <div className="flex items-center justify-center h-full text-sm text-slate-500 p-8 text-center">
            <div>
              <svg className="w-10 h-10 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p>PDF preview unavailable</p>
            </div>
          </div>
        ) : (
          <Document
            file={pdfUrl}
            onLoadSuccess={({ numPages: n }) => setNumPages(n)}
            onLoadError={() => setPdfError(true)}
            className="flex flex-col items-center py-4 gap-2"
          >
            {Array.from({ length: numPages }, (_, i) => (
              <Page
                key={i + 1}
                pageNumber={i + 1}
                width={380}
                className="shadow-sm"
              />
            ))}
          </Document>
        )}
      </div>

      {/* Right: Clause Cards */}
      <div className="w-3/5 overflow-y-auto space-y-3 pr-1">
        {clauses.length === 0 ? (
          <div className="premium-card flex items-center justify-center h-32 text-sm text-slate-500">
            No clauses extracted yet.
          </div>
        ) : (
          clauses.map((clause) => (
            <ClauseCard
              key={clause.clause_id}
              clause={clause}
              onUpdated={onClauseUpdated}
            />
          ))
        )}
      </div>
    </div>
  )
}
