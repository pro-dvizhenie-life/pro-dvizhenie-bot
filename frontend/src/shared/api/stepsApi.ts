import type { Step, Answers } from '../lib/types'

interface SendAnswerBody {
    step_code: string
    answers: { question_code: string; value: string | number | boolean | null }[]
}

export async function sendStepAnswer(
    publicId: string,
    stepCode: string,
    answers: Answers
): Promise<Step | null> {
    const body: SendAnswerBody = {
        step_code: stepCode,
        answers: Object.entries(answers).map(([code, value]) => ({
            question_code: code,
            value,
        })),
    }

    const res = await fetch(`/api/v1/applications/${publicId}/next/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
    })

    if (!res.ok) {
        throw new Error('Ошибка отправки ответов')
    }

    return (await res.json()) as Step | null
}

export async function fetchStepById(stepId: number): Promise<Step> {
    const res = await fetch(`/api/v1/steps/${stepId}/`, {
        credentials: 'include',
    })

    if (!res.ok) {
        throw new Error(`Ошибка загрузки шага ${stepId}`)
    }

    return (await res.json()) as Step
}