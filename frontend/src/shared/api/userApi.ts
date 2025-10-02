import type { Step, Answers } from '../lib/types'

interface PublicIdResponse {
    public_id: string
    current_stage: number
    current_step: Step
    answers: Answers
}

export async function getPublicId(): Promise<PublicIdResponse> {
    const res = await fetch('/api/v1/applications/forms/default/sessions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({}),
    })

    if (!res.ok) {
        throw new Error('Ошибка при получении public_id')
    }

    return (await res.json()) as PublicIdResponse
}