from .forms import GlobalSearchForm

def global_search_form(request):
    """Добавляет форму глобального поиска в контекст всех шаблонов."""
    return {
        'global_search_form': GlobalSearchForm()
    }

def user_avatar_processor(request):
    """Определяет иконку аватара в зависимости от группы пользователя."""
    if not request.user.is_authenticated:
        return {'user_avatar': 'icons/avatar-default.svg'}

    # Словарь: ID группы -> имя файла иконки
    # Вы можете легко добавлять сюда новые группы
    GROUP_AVATARS = {
        2: 'avatar-manager.svg',    # Менеджер
        1: 'avatar-storekeeper.svg',     # кладовщик
        4: 'avatar-production.svg', # производственник
        5: 'avatar-accountant.svg', # бухгалтер
    }

    # По умолчанию для всех авторизованных
    avatar_file = 'avatar.svg'

    if request.user.is_superuser:
        avatar_file = 'avatar-boss.svg'
    else:
        # Получаем ID всех групп, в которых состоит юзер
        user_group_ids = request.user.groups.values_list('id', flat=True)
        
        # Ищем первое совпадение ID группы в нашем словаре
        for group_id in user_group_ids:
            if group_id in GROUP_AVATARS:
                avatar_file = GROUP_AVATARS[group_id]
                break

    return {
        'user_avatar': f'icons/{avatar_file}'
    }