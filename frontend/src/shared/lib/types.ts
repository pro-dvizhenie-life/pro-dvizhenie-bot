// Варианты типов вопросов
export enum QuestionType {
    Text = 'text',
    YesNo = 'yes_no',
    SelectOne = 'select_one',
    SelectMultiple = 'select_multiple',
    Date = 'date',
    File = 'file',
}

// Опция для вопросов select/yes_no
export type QuestionOption = {
    value: string
    label: string
    order?: number
}

// Вопрос анкеты
export type Question = {
    code: string
    type: QuestionType
    title: string
    required?: boolean
    options?: QuestionOption[]
    payload?: string
    stageNumber?: number
}

// Шаг анкеты
export type Step = {
    id: number
    code: string
    title: string
    order?: number
    questions: Question[]
}

// Ответы на вопросы (словарь)
export type Answers = Record<string, string | number | boolean | null>

// Ошибка валидации
export type ApiError = {
    question: string
    message: string
}

// Ошибка документа (заготовка)
export type DocumentError = Record<string, unknown>

//  Статусы анкеты
export enum ApplicationStatus {
    Draft = 'draft',
    Submitted = 'submitted',
    UnderReview = 'under_review',
    Approved = 'approved',
    Rejected = 'rejected',
}
