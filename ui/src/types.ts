// The shape the backend returns. Declaring it once means TypeScript catches a
// typo like answer.refusalReason instead of finding out at runtime.
export type Source = {
  // The passage number the answer text refers to. Not a list position -
  // renumbering these from a map index makes the citations point at the
  // wrong passage.
  number: number
  citation: string
  text: string
}

export type Passage = {
  score: number
  citation: string
}

export type Answer = {
  question: string
  text: string
  refused: boolean
  refusal_reason: string
  llm_called: boolean
  provider: string
  sources: Source[]
  retrieved: Passage[]
}
