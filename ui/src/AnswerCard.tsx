import type { Answer } from './types'

// A second component, taking data through props. Splitting it out keeps App
// about "what happens" and leaves this one about "how it looks".
export function AnswerCard({ answer }: { answer: Answer }) {
  return (
    <div className="mt-8 space-y-4">
      {answer.refused ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-5">
          <p className="font-medium text-amber-900">No answer given</p>
          <p className="mt-1 text-amber-800">{answer.text}</p>
          <p className="mt-3 text-sm text-amber-700">
            Reason: {answer.refusal_reason}
          </p>
          {!answer.llm_called && (
            <p className="mt-1 text-sm text-amber-700">
              The model was never called — the question was rejected at retrieval,
              so this refusal cost nothing.
            </p>
          )}
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-500">{answer.provider}</p>
          <p className="mt-2 text-lg leading-relaxed">{answer.text}</p>

          <p className="mt-5 text-sm font-medium text-slate-500">Sources</p>
          <ul className="mt-2 space-y-2">
            {answer.sources.map((source) => (
              <li key={source.number} className="rounded-md bg-slate-50 p-3">
                <span className="text-sm font-medium text-slate-900">
                  [{source.number}] {source.citation}
                </span>
                <p className="mt-1 text-sm text-slate-600">{source.text}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <details className="rounded-lg border border-slate-200 bg-white p-5">
        <summary className="cursor-pointer text-sm font-medium text-slate-600">
          Retrieved passages ({answer.retrieved.length})
        </summary>
        <ul className="mt-3 space-y-1">
          {answer.retrieved.map((passage) => (
            <li key={passage.citation} className="flex gap-3 text-sm">
              <span className="w-12 shrink-0 text-right font-mono text-slate-400">
                {passage.score.toFixed(2)}
              </span>
              <span className="text-slate-600">{passage.citation}</span>
            </li>
          ))}
        </ul>
      </details>
    </div>
  )
}
