import { useEffect } from 'react'
import { useAppDispatch, useAppSelector } from '../../shared/hooks/redux'
import { initPublicId } from '../../store/slices/userSlice'
import { setStep, selectStep } from '../../store/slices/stepsSlice'
import type { Step } from '../../shared/lib/types'
import { DynamicStep } from '../../features/dynamicStep/dynamicStep'

export const StepPage = () => {
    const dispatch = useAppDispatch()
    const step = useAppSelector(selectStep)

    useEffect(() => {
        dispatch(initPublicId())
            .unwrap()
            .then((data: { publicId: string; currentStep: Step }) => {
                console.log('session:', data)
                if (data?.currentStep) {
                    dispatch(setStep(data.currentStep))
                }
            })
            .catch((e) => console.error('init error:', e))
    }, [dispatch])

    useEffect(() => {
        if (step) console.log('step in store:', step)
    }, [step])

    return <DynamicStep />
}