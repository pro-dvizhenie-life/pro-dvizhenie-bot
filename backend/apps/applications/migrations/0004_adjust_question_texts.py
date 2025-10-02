from django.db import migrations


def forwards(apps, schema_editor):
    Question = apps.get_model('applications', 'Question')
    Option = apps.get_model('applications', 'Option')
    Step = apps.get_model('applications', 'Step')

    updates = [
        {
            'code': 'q_tsrs_in_ipra',
            'type': 'textarea',
            'label': 'Расскажите, прописано ли ТСР в медзаключении или ИПРА',
            'help_text': 'Если нет, опишите, с какими сложностями столкнулись.',
        },
        {
            'code': 'q_deadline_need',
            'type': 'textarea',
            'label': 'Напишите, есть ли важные сроки, к которым нужна помощь',
            'help_text': 'Например, реабилитация, соревнования или другой дедлайн.',
        },
        {
            'code': 'q_need_consulting',
            'type': 'textarea',
            'label': (
                'Нужна ли вам консультационная помощь в составлении рекомендаций ИПРА, '
                'прохождении МСЭ, получении ТСР от СФР?'
            ),
            'help_text': 'Ответьте текстом: какие консультации пригодятся?',
        },
    ]

    for params in updates:
        question = Question.objects.filter(code=params['code']).first()
        if not question:
            continue
        question.type = params['type']
        question.label = params['label']
        payload = question.payload or {}
        payload['help_text'] = params['help_text']
        if 'hidden' in params:
            payload['hidden'] = params['hidden']
        question.payload = payload
        question.save(update_fields=['type', 'label', 'payload'])

    question = Question.objects.filter(code='q_need_consulting').first()
    if question:
        Option.objects.filter(question=question).delete()

    step_intro = Step.objects.filter(code='s0_intro', survey__code='default').first()
    if step_intro:
        question, _ = Question.objects.get_or_create(
            step=step_intro,
            code='q_application_date',
            defaults={
                'type': 'date',
                'label': 'Дата заполнения заявки',
                'required': False,
                'payload': {'order': 30, 'hidden': True, 'help_text': 'Определяется автоматически.'},
            },
        )
        question.type = 'date'
        question.label = 'Дата заполнения заявки'
        payload = question.payload or {}
        payload.update({'order': 30, 'hidden': True, 'help_text': 'Определяется автоматически.'})
        question.payload = payload
        question.required = False
        question.save(update_fields=['type', 'label', 'payload', 'required'])


def backwards(apps, schema_editor):
    Question = apps.get_model('applications', 'Question')
    Option = apps.get_model('applications', 'Option')
    Step = apps.get_model('applications', 'Step')

    reverses = [
        {
            'code': 'q_tsrs_in_ipra',
            'type': 'boolean',
            'label': 'Прописано ли ТСР в медзаключении или ИПРА?',
            'help_text': 'Если нет, расскажите почему.',
        },
        {
            'code': 'q_deadline_need',
            'type': 'date',
            'label': 'Есть ли важные сроки, к которым нужна помощь?',
            'help_text': 'Например, реабилитация или соревнования.',
        },
        {
            'code': 'q_need_consulting',
            'type': 'multiselect',
            'label': 'Нужна ли консультационная помощь?',
            'help_text': 'Можно выбрать несколько вариантов.',
        },
    ]

    for params in reverses:
        question = Question.objects.filter(code=params['code']).first()
        if not question:
            continue
        question.type = params['type']
        question.label = params['label']
        payload = question.payload or {}
        payload['help_text'] = params['help_text']
        question.payload = payload
        question.save(update_fields=['type', 'label', 'payload'])

    question = Question.objects.filter(code='q_need_consulting').first()
    if question:
        Option.objects.filter(question=question).delete()
        Option.objects.create(question=question, value='ipra', label='Да, по ИПРА', order=1)
        Option.objects.create(question=question, value='mse', label='Да, по МСЭ', order=2)
        Option.objects.create(question=question, value='sfr', label='Да, по СФР', order=3)
        Option.objects.create(question=question, value='none', label='Нет', order=4)

    step_intro = Step.objects.filter(code='s0_intro', survey__code='default').first()
    if step_intro:
        Question.objects.filter(step=step_intro, code='q_application_date').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0003_alter_question_type'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
