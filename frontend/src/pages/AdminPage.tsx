import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Sidebar from '../components/layout/Sidebar'
import TopBar from '../components/layout/TopBar'
import { useAuth } from '../hooks/useAuth'
import { adminApi } from '../api/admin'
import { usersApi } from '../api/users'
import type { ClearPlaybookDataResponse } from '../api/admin'
import type { UserCreate } from '../api/users'
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
const RULE_TYPES = ['REQUIRED', 'FORBIDDEN'] as const

const emptyForm = (): PlaybookRuleCreate => ({
  clause_type: CLAUSE_TYPES[0],
  jurisdiction: JURISDICTIONS[0],
  rule_type: 'REQUIRED',
  description: '',
  weight: 1.0,
})

export default function AdminPage() {
  const { hasRole } = useAuth()

  const [activeTab, setActiveTab] = useState<'rules' | 'users'>('rules')
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const [jurisdictionFilter, setJurisdictionFilter] = useState<string>('')
  const [pdfUploading, setPdfUploading] = useState(false)
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [clearResult, setClearResult] = useState<ClearPlaybookDataResponse | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<PlaybookRuleCreate>(emptyForm())
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null)
  const [editRule, setEditRule] = useState<Partial<PlaybookRuleCreate & { is_active: boolean }>>({})
  const [userForm, setUserForm] = useState<UserCreate>({
    email: '',
    password: '',
    role: 'junior_lawyer',
    tenant_id: 'tenant_abc',
  })
  const [userSaving, setUserSaving] = useState(false)
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null)

  const {
    data: rules = [],
    isLoading: loading,
    isError: rulesLoadError,
    refetch: refetchRules,
  } = useQuery({
    queryKey: ['admin-playbook-rules', jurisdictionFilter],
    queryFn: () => adminApi.listRules(jurisdictionFilter || undefined),
    enabled: hasRole('admin'),
  })

  const {
    data: users = [],
    isLoading: usersLoading,
    isError: usersLoadError,
    refetch: refetchUsers,
  } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => usersApi.list(),
    enabled: hasRole('admin'),
  })

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  if (!hasRole('admin')) {
    return <Navigate to="/dashboard" replace />
  }

  const handleClearPlaybook = async () => {
    setClearing(true)
    setClearResult(null)
    try {
      const result = await adminApi.clearPlaybookData()
      setClearResult(result)
      showToast(`Cleared ${result.postgres_rules_deleted} rules from all databases.`)
      setShowClearConfirm(false)
      refetchRules()
    } catch {
      setError('Failed to clear playbook data. Please try again.')
      setShowClearConfirm(false)
    } finally {
      setClearing(false)
    }
  }

  const handleDisable = async (id: number) => {
    try {
      await adminApi.deleteRule(id)
      showToast('Rule deleted successfully.')
      refetchRules()
    } catch {
      setError('Failed to disable rule.')
    }
  }

  const startEditingRule = (rule: PlaybookRule) => {
    setEditingRuleId(rule.id)
    setEditRule({
      description: rule.description,
      weight: rule.weight,
      is_active: rule.is_active,
    })
  }

  const handleRuleUpdate = async (id: number) => {
    try {
      await adminApi.updateRule(id, editRule)
      showToast('Rule updated successfully.')
      setEditingRuleId(null)
      setEditRule({})
      refetchRules()
    } catch {
      setError('Failed to update rule.')
    }
  }

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setUserSaving(true)
    try {
      await usersApi.create(userForm)
      showToast('User created successfully.')
      setUserForm({
        email: '',
        password: '',
        role: 'junior_lawyer',
        tenant_id: userForm.tenant_id,
      })
      refetchUsers()
    } catch {
      setError('Failed to create user.')
    } finally {
      setUserSaving(false)
    }
  }

  const handleUserUpdate = async (
    userId: string,
    data: { role?: string; is_active?: boolean }
  ) => {
    setUpdatingUserId(userId)
    try {
      await usersApi.update(userId, data)
      showToast('User updated successfully.')
      refetchUsers()
    } catch {
      setError('Failed to update user.')
    } finally {
      setUpdatingUserId(null)
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
      refetchRules()
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
      refetchRules()
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
    <div className="app-shell">
      <Sidebar />
      <div className="workspace">
        <TopBar />
        <main className="premium-main">
          <div className="max-w-6xl mx-auto space-y-6 soft-appear">

            {/* Toast */}
            {toast && (
              <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
                {toast}
              </div>
            )}

            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-slate-950">Admin</h1>
                <p className="text-sm text-slate-500 mt-1">
                  Manage playbook rules and users
                </p>
              </div>
              {activeTab === 'rules' && (
                <div className="flex items-center gap-2">
                <label
                  className={`btn-secondary cursor-pointer ${pdfUploading ? 'opacity-50 pointer-events-none' : ''}`}
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
                  className="btn-primary"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Rule
                </button>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 border-b border-slate-200">
              <button
                onClick={() => setActiveTab('rules')}
                className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'rules'
                    ? 'border-amber-600 text-slate-950'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                Playbook Rules
              </button>
              <button
                onClick={() => setActiveTab('users')}
                className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'users'
                    ? 'border-amber-600 text-slate-950'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                Users
              </button>
            </div>

            {activeTab === 'rules' && (
              <>
            {/* Add Rule Form */}
            {showForm && (
              <div className="premium-panel p-6">
                <h2 className="text-base font-semibold text-slate-950 mb-4">New Playbook Rule</h2>
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
            {(error || rulesLoadError) && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
                {error ?? 'Failed to load playbook rules. Please try again.'}
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
                    {rules.map((rule) => {
                      const isEditing = editingRuleId === rule.id
                      return (
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
                          {isEditing ? (
                            <input
                              value={editRule.description ?? ''}
                              onChange={(e) => setEditRule((prev) => ({ ...prev, description: e.target.value }))}
                              className="w-full min-w-64 border border-gray-300 rounded px-2 py-1 text-sm"
                            />
                          ) : (
                            rule.description
                          )}
                        </td>
                        <td className="px-5 py-3 text-sm text-gray-600 whitespace-nowrap">
                          {isEditing ? (
                            <input
                              type="number"
                              value={editRule.weight ?? rule.weight}
                              onChange={(e) => setEditRule((prev) => ({ ...prev, weight: Number(e.target.value) }))}
                              className="w-20 border border-gray-300 rounded px-2 py-1 text-sm"
                              min={0}
                              max={10}
                              step={0.1}
                            />
                          ) : (
                            rule.weight.toFixed(1)
                          )}
                        </td>
                        <td className="px-5 py-3 whitespace-nowrap">
                          {isEditing ? (
                            <label className="inline-flex items-center gap-2 text-xs text-gray-600">
                              <input
                                type="checkbox"
                                checked={editRule.is_active ?? rule.is_active}
                                onChange={(e) => setEditRule((prev) => ({ ...prev, is_active: e.target.checked }))}
                              />
                              Active
                            </label>
                          ) : rule.is_active ? (
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
                        <td className="px-5 py-3 text-right whitespace-nowrap space-x-3">
                          {isEditing ? (
                            <>
                              <button
                                onClick={() => handleRuleUpdate(rule.id)}
                                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
                              >
                                Save
                              </button>
                              <button
                                onClick={() => { setEditingRuleId(null); setEditRule({}) }}
                                className="text-xs text-gray-500 hover:text-gray-700 font-medium transition-colors"
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => startEditingRule(rule)}
                                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDisable(rule.id)}
                                className="text-xs text-red-600 hover:text-red-800 font-medium transition-colors"
                              >
                                Delete
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}
            </div>
            {/* Danger Zone */}
            <div className="border border-red-200 rounded-xl overflow-hidden shadow-sm">
              <div className="bg-red-50 px-5 py-3 border-b border-red-200">
                <h2 className="text-sm font-semibold text-red-700">Danger Zone</h2>
              </div>
              <div className="bg-white px-5 py-4 flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-900">Clear All Playbook Data</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Permanently deletes all playbook rules from PostgreSQL, Qdrant, and Neo4j.
                    This cannot be undone.
                  </p>
                  {clearResult && (
                    <p className="text-xs text-green-700 mt-1.5 font-medium">
                      Last clear: {clearResult.postgres_rules_deleted} rules deleted from PostgreSQL,{' '}
                      {clearResult.qdrant_collection_cleared ? 'Qdrant collection cleared' : 'Qdrant unchanged'},{' '}
                      {clearResult.neo4j_nodes_deleted} Neo4j nodes removed.
                    </p>
                  )}
                </div>
                <button
                  onClick={() => setShowClearConfirm(true)}
                  className="shrink-0 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
                >
                  Clear All Playbook Data
                </button>
              </div>
            </div>
              </>
            )}

            {activeTab === 'users' && (
              <div className="space-y-6">
                <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                  <h2 className="text-base font-semibold text-gray-900 mb-4">Create User</h2>
                  <form onSubmit={handleCreateUser} className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
                    <div className="md:col-span-2">
                      <label className="block text-xs font-medium text-gray-700 mb-1">Email</label>
                      <input
                        type="email"
                        value={userForm.email}
                        onChange={(e) => setUserForm((prev) => ({ ...prev, email: e.target.value }))}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Password</label>
                      <input
                        type="password"
                        value={userForm.password}
                        onChange={(e) => setUserForm((prev) => ({ ...prev, password: e.target.value }))}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        minLength={8}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Role</label>
                      <select
                        value={userForm.role}
                        onChange={(e) => setUserForm((prev) => ({ ...prev, role: e.target.value as UserCreate['role'] }))}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="junior_lawyer">Junior Lawyer</option>
                        <option value="senior_lawyer">Senior Lawyer</option>
                        <option value="admin">Admin</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Tenant</label>
                      <input
                        value={userForm.tenant_id}
                        onChange={(e) => setUserForm((prev) => ({ ...prev, tenant_id: e.target.value }))}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        required
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={userSaving}
                      className="md:col-start-5 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                    >
                      {userSaving ? 'Creating...' : 'Create User'}
                    </button>
                  </form>
                </div>

                {(error || usersLoadError) && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
                    {error ?? 'Failed to load users. Please try again.'}
                  </div>
                )}

                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                  {usersLoading ? (
                    <div className="flex items-center justify-center py-16">
                      <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                      <span className="ml-3 text-sm text-gray-500">Loading users...</span>
                    </div>
                  ) : users.length === 0 ? (
                    <div className="text-center py-16 text-sm text-gray-500">No users found.</div>
                  ) : (
                    <table className="min-w-full divide-y divide-gray-100">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Email</th>
                          <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Role</th>
                          <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Tenant</th>
                          <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
                          <th className="px-5 py-3" />
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {users.map((user) => (
                          <tr key={user.user_id} className="hover:bg-gray-50 transition-colors">
                            <td className="px-5 py-3 text-sm text-gray-900">{user.email}</td>
                            <td className="px-5 py-3">
                              <select
                                value={user.role}
                                disabled={updatingUserId === user.user_id}
                                onChange={(e) => handleUserUpdate(user.user_id, { role: e.target.value })}
                                className="border border-gray-300 rounded px-2 py-1 text-xs text-gray-700"
                              >
                                <option value="junior_lawyer">Junior Lawyer</option>
                                <option value="senior_lawyer">Senior Lawyer</option>
                                <option value="admin">Admin</option>
                              </select>
                            </td>
                            <td className="px-5 py-3 text-sm text-gray-600">{user.tenant_id}</td>
                            <td className="px-5 py-3">
                              <span className={`text-xs font-medium ${user.is_active ? 'text-green-700' : 'text-gray-400'}`}>
                                {user.is_active ? 'Active' : 'Disabled'}
                              </span>
                            </td>
                            <td className="px-5 py-3 text-right">
                              <button
                                onClick={() => handleUserUpdate(user.user_id, { is_active: !user.is_active })}
                                disabled={updatingUserId === user.user_id}
                                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium disabled:opacity-50 transition-colors"
                              >
                                {user.is_active ? 'Disable' : 'Enable'}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            )}

            {/* Confirm dialog */}
            {showClearConfirm && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
                  <h3 className="text-base font-semibold text-gray-900 mb-2">Are you sure?</h3>
                  <p className="text-sm text-gray-600 mb-5">
                    This will permanently delete all playbook rules from PostgreSQL, Qdrant, and
                    Neo4j. This action cannot be undone.
                  </p>
                  <div className="flex items-center gap-3 justify-end">
                    <button
                      onClick={() => setShowClearConfirm(false)}
                      disabled={clearing}
                      className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleClearPlaybook}
                      disabled={clearing}
                      className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                    >
                      {clearing ? 'Clearing…' : 'Yes, clear all'}
                    </button>
                  </div>
                </div>
              </div>
            )}

          </div>
        </main>
      </div>
    </div>
  )
}
