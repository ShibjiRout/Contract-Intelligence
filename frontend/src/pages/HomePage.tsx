import { useNavigate } from 'react-router-dom'

const features = [
  {
    title: 'OCR Extraction',
    description:
      'Upload PDF or DOCX contracts and let Azure AI Document Intelligence extract every clause with precision.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    ),
  },
  {
    title: 'Risk Analysis',
    description:
      'Parallel checks across your playbook rules, accepted wording database, and counterparty relationship graph produce a clear Green / Amber / Red risk rating.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
  },
  {
    title: 'Smart Recommendations',
    description:
      'For every high-risk clause the platform suggests a revised wording, letting senior lawyers approve, reject, or modify with a single click.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
        />
      </svg>
    ),
  },
]

export default function HomePage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="border-b border-slate-200 bg-white/80 sticky top-0 z-10 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="text-lg font-bold text-slate-950">Contract Intelligence</span>
          <button
            onClick={() => navigate('/login')}
            className="btn-primary"
          >
            Sign In
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="flex-1">
        <div className="max-w-6xl mx-auto px-6 py-24 text-center">
          <span className="inline-block px-3 py-1 bg-amber-100 text-amber-800 text-xs font-semibold rounded-full uppercase tracking-wide mb-6 ring-1 ring-amber-200">
            Powered by GPT-4o + LangGraph
          </span>
          <h1 className="text-5xl font-extrabold text-slate-950 leading-tight mb-6 tracking-tight">
            AI-Powered Contract Review
          </h1>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto mb-10">
            Upload a contract, get instant clause extraction, jurisdiction-aware risk scoring, and
            actionable recommendations — all reviewed by your legal team on a single dashboard.
          </p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => navigate('/login')}
              className="btn-primary px-6 py-3"
            >
              Get Started
            </button>
            <button
              onClick={() => navigate('/login')}
              className="btn-secondary px-6 py-3"
            >
              Sign In
            </button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-white/70">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-4">
            Everything your team needs
          </h2>
          <p className="text-gray-500 text-center mb-14 max-w-xl mx-auto">
            A complete pipeline from raw document to lawyer-approved decision, with full audit trail.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {features.map((f) => (
              <div
                key={f.title}
                className="premium-card premium-card-hover p-6"
              >
                <div className="w-12 h-12 bg-amber-100 text-teal-800 rounded-lg flex items-center justify-center mb-4">
                  {f.icon}
                </div>
                <h3 className="text-base font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-8 bg-white">
        <div className="max-w-6xl mx-auto px-6 text-center text-sm text-gray-400">
          &copy; {new Date().getFullYear()} Contract Intelligence Platform. All rights reserved.
        </div>
      </footer>
    </div>
  )
}
