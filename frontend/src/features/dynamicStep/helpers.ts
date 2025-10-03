import type { Question } from '../../shared/lib/types'

const qType = (q: Question): string => String((q as any).type)

export const isYesNo    = (q: Question) => ['boolean', 'yes_no'].includes(qType(q))
export const isSelect   = (q: Question) => ['select', 'select_one'].includes(qType(q))
export const isText     = (q: Question) => qType(q) === 'text'
export const isDate     = (q: Question) => qType(q) === 'date'
export const isPhone    = (q: Question) => qType(q) === 'phone' || q.code === 'q_phone'
export const isEmailQ   = (q: Question) => qType(q) === 'email' || q.code === 'q_email'
export const isTextarea = (q: Question) => qType(q) === 'textarea'

export const getOptions = (q?: Question) => {
    const raw = (q as any)?.options ?? []
    if (!Array.isArray(raw)) return []
    return raw.map((o: any) => ({
        value: o.value ?? o.code ?? o.id ?? '',
        label: o.label ?? o.title ?? o.name ?? String(o.value ?? o.code ?? o.id ?? ''),
    }))
}

export const getQuestionText = (q: Question) =>
    (q as any).label ?? (q as any).title ?? q.code

export const NEED_CONSULTING_OPTIONS = [
    { value: 'ipra',    label: 'ИПРА' },
    { value: 'mse',     label: 'МСЭ' },
    { value: 'sfr_tsr', label: 'ТСР от СФР' },
    { value: 'other',   label: 'Другое' },
]