from .forms import GlobalSearchForm


def global_search_form(request):
    """Добавляет форму глобального поиска в контекст всех шаблонов."""
    return {
        'global_search_form': GlobalSearchForm()
    }

def user_avatar_processor(request):
    """Определяет иконку аватара по ключевым словам в названии групп пользователя."""
    
    DEFAULT_AVATAR = 'icons/avatar-default.svg'
    
    if not request.user.is_authenticated:
        return {'user_avatar': DEFAULT_AVATAR}

    if request.user.is_superuser:
        return {'user_avatar': 'icons/avatar-boss.svg'}

    # Карта: Ключевое слово в названии группы -> Файл иконки
    # Порядок важен: первое совпадение выигрывает
    AVATAR_MAP = {
    'manager': 'avatar-manager.svg',
    'менеджер': 'avatar-manager.svg',
    'store': 'avatar-storekeeper.svg',
    'склад': 'avatar-storekeeper.svg',
    'клад': 'avatar-storekeeper.svg',
    'prod': 'avatar-production.svg',
    'производст': 'avatar-production.svg',
    'бухг': 'avatar-accountant.svg',
    'управл': 'avatar-administrator.svg',
    }

    try:
        # Получаем все названия групп пользователя одним запросом в нижнем регистре
        user_group_names = list(request.user.groups.values_list('name', flat=True))
        user_group_names_lower = [name.lower() for name in user_group_names]

        # Ищем совпадение
        for key, icon_file in AVATAR_MAP.items():
            # Если ключевое слово содержится в ЛЮБОМ из названий групп юзера
            if any(key in group_name for group_name in user_group_names_lower):
                return {'user_avatar': f'icons/{icon_file}'}

    except Exception:
        # Если вдруг база недоступна или ошибка в логике — возвращаем дефолт
        return {'user_avatar': DEFAULT_AVATAR}

    # Если юзер авторизован, но его группы не подошли под описание
    return {'user_avatar': 'icons/avatar.svg'}