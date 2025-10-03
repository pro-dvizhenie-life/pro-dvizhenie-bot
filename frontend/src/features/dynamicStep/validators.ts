export const nonEmpty = (v: unknown) =>
    v !== undefined && v !== null && String(v).trim() !== ''

export const isEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)

export const isYmdNotFuture = (v: string) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return false
    const [y, m, d] = v.split('-').map(Number)
    const dt = new Date(y, m - 1, d)
    if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) return false
    const today = new Date()
    const strip = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
    return strip(dt) <= strip(today)
}

export const isPhoneAcceptable = (s: string) => {
    const x = s.trim()
    if (/^\+7\d{10}$/.test(x)) return true
    if (/^\+7 \d{3} \d{3} \d{2} \d{2}$/.test(x)) return true
    if (/^8\d{10}$/.test(x)) return true
    if (/^\d{10}$/.test(x)) return true
    const digits = x.replace(/\D/g, '')
    if (digits.length === 11 && (digits[0] === '7' || digits[0] === '8')) return true
    if (digits.length === 10) return true
    return false
}

export function ruToIsoDate(input: string): string | null {
    const m = input.trim().match(/^(\d{2})\.(\d{2})\.(\d{4})$/)
    if (!m) return null
    const [, ddStr, mmStr, yyyyStr] = m
    const dd = Number(ddStr), mm = Number(mmStr), yyyy = Number(yyyyStr)
    if (mm < 1 || mm > 12) return null
    if (dd < 1 || dd > 31) return null
    const d = new Date(yyyy, mm - 1, dd)
    if (d.getFullYear() !== yyyy || d.getMonth() !== mm - 1 || d.getDate() !== dd) return null
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    if (d.getTime() > today.getTime()) return null
    const mmIso = String(mm).padStart(2, '0')
    const ddIso = String(dd).padStart(2, '0')
    return `${yyyy}-${mmIso}-${ddIso}`
}

export function isoToRuDate(iso?: string | null): string {
    if (!iso) return ''
    const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/)
    if (!m) return ''
    const [, yyyy, mm, dd] = m
    return `${dd}.${mm}.${yyyy}`
}