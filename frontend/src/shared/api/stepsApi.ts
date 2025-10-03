import type { Step, Answers } from '../lib/types'

type SendAnswerRow = { question_code: string; value: any }
type SendAnswerBody = { step_code: string; answers: SendAnswerRow[] }

function normalizePhone(raw: string): string {
    let d = String(raw).replace(/[^\d]/g, '')
    if (d.startsWith('8')) d = '7' + d.slice(1)
    if (!d.startsWith('7') && d.length === 10) d = '7' + d
    if (d.length !== 11 || d[0] !== '7') return String(raw).trim()
    return `+${d}`
}

export async function sendStepAnswer(
    publicId: string,
    stepCode: string,
    answers: Answers
): Promise<Step | null> {
    const rows: SendAnswerRow[] = Object.entries(answers).map(([code, v]) => {
        let value: any = v
        if (code === 'q_phone' && value != null) value = normalizePhone(String(value))
        if (code === 'q_email' && typeof value === 'string') value = value.trim().toLowerCase()
        return { question_code: code, value }
    })
    const body: SendAnswerBody = { step_code: stepCode, answers: rows }
    const res = await fetch(`/api/v1/applications/${publicId}/next/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
    })
    if (!res.ok) {
        let server: any = null
        try { server = await res.json() } catch {}
        const err: any = { kind: 'HttpError', status: res.status, url: res.url, requestBody: body, server }
        throw err
    }
    const data = (await res.json()) as Step | null
    return data
}

export async function fetchStepById(stepId: number): Promise<Step> {
    const res = await fetch(`/api/v1/steps/${stepId}/`, { credentials: 'include' })
    if (!res.ok) throw new Error(`Ошибка загрузки шага ${stepId}`)
    return (await res.json()) as Step
}