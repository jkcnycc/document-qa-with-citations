import { useState } from 'react'
import type { Answer } from './types'
import { AnswerCard } from './AnswerCard'

const EXAMPLES = [
  'How long do I have to request a refund?',
  'What are the API rate limits on the Growth plan?',
  'Does Meridian support Kubernetes deployment?',
]

export default function App() {
  const [question, setQuestion] = useState('')
  // Three pieces of state, because a request has three outcomes and the screen
  // has to show a different thing for each.
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function ask(text: string) {
    setLoading(true)
    setError(null)
    setAnswer(null)
    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text }),
      })
      if (!response.ok) {
        throw new Error(`The server returned ${response.status}`)
      }
      setAnswer(await response.json())
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Request failed')
    } finally {
      // finally, so the spinner stops whether it worked or not - forgetting
      // this is how a UI ends up stuck loading forever.
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-3xl px-6 py-14">
        <h1 className="text-3xl font-semibold tracking-tight">Document Q&amp;A</h1>
        <p className="mt-2 text-slate-500">
          Answers come only from the indexed documents, and every claim shows its
          source. When the documents do not cover the question, it says so.
        </p>

        <form
          className="mt-8 flex gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            ask(question)
          }}
        >
          <input
            className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-3
                       outline-none focus:border-slate-900 disabled:bg-slate-100"
            placeholder="Ask something about the documents"
            value={question}
            disabled={loading}
            onChange={(event) => setQuestion(event.target.value)}
          />
          <button
            className="rounded-lg bg-slate-900 px-6 py-3 font-medium text-white
                       transition hover:bg-slate-700 disabled:opacity-40"
            disabled={loading || question.trim() === ''}
          >
            {loading ? 'Asking…' : 'Ask'}
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            // key lets React tell list items apart between renders. Leaving it
            // off is the warning every React beginner sees first.
            <button
              key={example}
              type="button"
              disabled={loading}
              onClick={() => {
                setQuestion(example)
                ask(example)
              }}
              className="rounded-full border border-slate-200 bg-white px-3 py-1
                         text-sm text-slate-600 hover:border-slate-400 disabled:opacity-40"
            >
              {example}
            </button>
          ))}
        </div>

        {error && (
          <div className="mt-8 rounded-lg border border-red-200 bg-red-50 p-5 text-red-800">
            {error}
          </div>
        )}

        {answer && <AnswerCard answer={answer} />}
      </div>
    </div>
  )
}
