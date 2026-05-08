import { useState, useRef, useEffect } from 'react'
import { saveAs } from 'file-saver'
import { Document, Paragraph, TextRun, HeadingLevel, Packer } from 'docx'
import type { Clause } from '../../types'

interface Props {
  contractFileName: string
  clauses: Clause[]
}

export default function ExportMenu({ contractFileName, clauses }: Props) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleExportPdf = () => {
    setOpen(false)
    window.print()
  }

  const handleExportDocx = async () => {
    setOpen(false)

    const children = [
      new Paragraph({
        text: `Contract Review: ${contractFileName}`,
        heading: HeadingLevel.HEADING_1,
      }),
      new Paragraph({
        children: [new TextRun({ text: `Generated: ${new Date().toLocaleString()}`, italics: true })],
      }),
      new Paragraph({ text: '' }),
    ]

    for (const clause of clauses) {
      children.push(
        new Paragraph({
          text: clause.clause_type,
          heading: HeadingLevel.HEADING_2,
        }),
        new Paragraph({
          children: [
            new TextRun({ text: 'Risk Level: ', bold: true }),
            new TextRun({ text: clause.risk_level }),
          ],
        }),
        new Paragraph({
          children: [
            new TextRun({ text: 'Text: ', bold: true }),
            new TextRun({ text: clause.raw_text }),
          ],
        }),
      )

      if (clause.recommendation) {
        children.push(
          new Paragraph({
            children: [
              new TextRun({ text: 'Recommendation: ', bold: true }),
              new TextRun({ text: clause.recommendation }),
            ],
          })
        )
      }

      children.push(new Paragraph({ text: '' }))
    }

    const doc = new Document({ sections: [{ children }] })
    const buffer = await Packer.toBuffer(doc)
    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const baseName = contractFileName.replace(/\.[^/.]+$/, '')
    saveAs(blob, `${baseName}-review.docx`)
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm border border-gray-300 text-gray-700 px-3 py-1.5 rounded-md hover:bg-gray-50 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Export
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-lg z-20 overflow-hidden">
          <button
            onClick={handleExportPdf}
            className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
          >
            <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
            </svg>
            Export PDF
          </button>
          <button
            onClick={handleExportDocx}
            className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2 border-t border-gray-100"
          >
            <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
            </svg>
            Export DOCX
          </button>
        </div>
      )}
    </div>
  )
}
