import cls from './PageError.module.css'

export const PageError: React.FC = () => {
	const reloadPage = () => {
		window.location.reload()
	}
	return (
		<div className={cls.PageError}>
			<p>Произошла непредвиденная ошибка</p>
			<button type='button' onClick={reloadPage}>
				Обновить страницу
			</button>
		</div>
	)
}
