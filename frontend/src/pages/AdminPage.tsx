import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'
import { useAuth } from '../hooks/useAuth'
import { adminApi } from '../api/admin'
import type { PlaybookRule, PlaybookRuleCreate } from '../types'

const CLAUSE_TYPES = [
  'CONFIDENTIALITY',
  'INDEMNITY',
  'LIABILITY',
  'TERMINATION',
  'GOVERNING_LAW',
  'DISPUTE_RESOLUTION',
  'FORCE_MAJEURE',
  'PAYMENT',
  'INTELLECTUAL_PROPERTY',
  'NON_COMPETE',
  'NON_SOLICITATION',
  'WARRANTY',
]

const JURISDICTIONS = ['UK', 'US', 'UAE']
const RULE_TYPES = ['REQUIRED', 'FORBIDDEN', 'CONDITIONAL'] as const

const emptyForm = (): PlaybookRuleCreate => ({
  clause_type: CLAUSE_TYPES[0],
  jurisdiction: JURISDICTIONS[0],
  rule_type: 'REQUIRED',
  description: '',
  weight: 1.0,
})

export default function AdminPage() {
  const { hasRole } = useAuth()

  const [rules, setRules] = useState<PlaybookRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const [jurisdictionFilter, setJurisdictionFilter] = useState<string>('')
  const [pdfUploading, setPdfUploading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<PlaybookRuleCreate>(emptyForm())
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  if (!hasRole('admin')) {
    return <Navigate to="/dashboard" replace />
  }

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  const loadRules = async (jurisdiction?: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminApi.listRules(jurisdiction || undefined)
      setRules(data)
    } catch {
      setError('Failed to load playbook rules. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRules(jurisdictionFilter)
  }, [jurisdictionFilter])

  const handleDisable = async (id: number) => {
    try {
      await adminApi.deleteRule(id)
      showToast('Rule deleted successfully.')
      loadRules(jurisdictionFilter)
    } catch {
      setError('Failed to disable rule.')
    }
  }

  const handleFormChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: name === 'weight' ? parseFloat(value) : value,
    }))
  }

  const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setPdfUploading(true)
    try {
      const res = await adminApi.uploadPdf(file)
      showToast(`${res.data.rules_created} rule${res.data.rules_created !== 1 ? 's' : ''} extracted from PDF.`)
      loadRules(jurisdictionFilter)
    } catch {
      setError('Failed to extract rules from PDF. Please try again.')
    } finally {
      setPdfUploading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    if (form.description.trim().length < 10) {
      setFormError('Description must be at least 10 characters.')
      return
    }
    if (form.weight < 0 || form.weight > 10) {
      setFormError('Weight must be between 0 and 10.')
      return
    }
    setSaving(true)
    try {
      await adminApi.createRule(form)
      showToast('Rule created successfully.')
      setShowForm(false)
      setForm(emptyForm())
      loadRules(jurisdictionFilter)
    } catch {
      setFormError('Failed to create rule. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const ruleTypeBadge = (rt: string) => {
    const styles: Record<string, string> = {
      REQUIRED: 'bg-green-100 text-green-700',
      FORBIDDEN: 'bg-red-100 text-red-700',
      CONDITIONAL: 'bg-yellow-100 text-yellow-700',
    }
    return (
      <span
        className={`px-2 py-0.5 rounded text-xs font-medium ${styles[rt] ?? 'bg-gray-100 text-gray-600'}`}
      >
        {rt}
      </span>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-6xl mx-auto space-y-6">

            {/* Toast */}
            {toast && (
              <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
                {toast}
              </div>
            )}

            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Playbook Rules</h1>
                <p className="text-sm text-gray-500 mt-0.5">
                  Manage jurisdiction-specific clause requirements
                </p>
              </div>
              <div className="flex items-center gap-2">
                <label
                  className={`inline-flex items-center gap-1.5 px-4 py-2 border border-indigo-300 text-indigo-700 text-sm font-medium rounded-lg hover:bg-indigo-50 transition-colors cursor-pointer ${pdfUploading ? 'opacity-50 pointer-events-none' : ''}`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  {pdfUploading ? 'Uploading…' : 'Upload PDF'}
                  <input
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={handlePdfUpload}
                    disabled={pdfUploading}
                  />
                </label>
                <button
                  onClick={() => { setShowForm(true); setFormError(null) }}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Rule
                </button>
              </div>
            </div>

            {/* Add Rule Form */}
            {showForm && (
              <div className="bg-white border border-indigo-200 rounded-xl p-6 shadow-sm">
                <h2 className="text-base font-semibold text-gray-900 mb-4">New Playbook Rule</h2>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Clause Type
                      </label>
                      <select
                        name="clause_type"
                        value={form.clause_type}
                        onChange={handleFormChange}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        {CLAUSE_TYPES.map((ct) => (
                          <option key={ct} value={ct}>
                            {ct.replace(/_/g, ' ')}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Jurisdiction
                      </label>
                      <select
                        name="jurisdiction"
                        value={form.jurisdiction}
                        onChange={handleFormChange}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        {JURISDICTIONS.map((j) => (
                          <option key={j} value={j}>
                            {j}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Rule Type
                      </label>
                      <select
                        name="rule_type"
                        value={form.rule_type}
                        onChange={handleFormChange}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        {RULE_TYPES.map((rt) => (
                          <option key={rt} value={rt}>
                            {rt}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Description
                      <span className="text-gray-400 font-normal ml-1">(min 10 chars)</span>
                    </label>
                    <textarea
                      name="description"
                      value={form.description}
                      onChange={handleFormChange}
                      rows={3}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                      placeholder="Describe the rule requirement..."
                    />
                  </div>

                  <div className="w-40">
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Weight
                      <span className="text-gray-400 font-normal ml-1">(0–10)</span>
                    </label>
                    <input
                      type="number"
                      name="weight"
                      value={form.weight}
                      onChange={handleFormChange}
                      min={0}
                      max={10}
                      step={0.1}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  {formError && (
                    <p className="text-sm text-red-600">{formError}</p>
                  )}

                  <div className="flex items-center gap-3">
                    <button
                      type="submit"
                      disabled={saving}
                      className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                    >
                      {saving ? 'Saving…' : 'Save Rule'}
                    </button>
                    <button
                      type="button"
                      onClick={() => { setShowForm(false); setForm(emptyForm()) }}
                      className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Filter */}
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-600 font-medium">Filter by jurisdiction:</label>
              <select
                value={jurisdictionFilter}
                onChange={(e) => setJurisdictionFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All</option>
                {JURISDICTIONS.map((j) => (
                  <option key={j} value={j}>
                    {j}
                  </option>
                ))}
              </select>
            </div>

            {/* Error banner */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {/* Table */}
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
              {loading ? (
                <div className="flex items-center justify-center py-16">
                  <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                  <span className="ml-3 text-sm text-gray-500">Loading rules…</span>
                </div>
              ) : rules.length === 0 ? (
                <div className="text-center py-16 text-sm text-gray-500">
                  No playbook rules found
                  {jurisdictionFilter ? ` for jurisdiction "${jurisdictionFilter}"` : ''}.
                </div>
              ) : (
                <table className="min-w-full divide-y divide-gray-100">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Clause Type
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Jurisdiction
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Rule Type
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Description
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Weight
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Status
                      </th>
                      <th className="px-5 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {rules.map((rule) => (
                      <tr key={rule.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-5 py-3 text-sm text-gray-900 font-medium whitespace-nowrap">
                          {rule.clause_type.replace(/_/g, ' ')}
                        </td>
                        <td className="px-5 py-3 text-sm text-gray-600 whitespace-nowrap">
                          {rule.jurisdiction}
                        </td>
                        <td className="px-5 py-3 whitespace-nowrap">
                          {ruleTypeBadge(rule.rule_type)}
                        </td>
                        <td className="px-5 py-3 text-sm text-gray-600 max-w-xs truncate">
                          {rule.description}
                        </td>
                        <td className="px-5 py-3 text-sm text-gray-600 whitespace-nowrap">
                          {rule.weight.toFixed(1)}
                        </td>
                        <td className="px-5 py-3 whitespace-nowrap">
                          {rule.is_active ? (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700">
                              <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                              Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-400">
                              <span className="w-1.5 h-1.5 bg-gray-300 rounded-full" />
                              Disabled
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-3 text-right whitespace-nowrap">
                          <button
                            onClick={() => handleDisable(rule.id)}
                            className="text-xs text-red-600 hover:text-red-800 font-medium transition-colors"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
