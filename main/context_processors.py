from .forms import GlobalSearchForm

def global_search_form(request):
    """Добавляет форму глобального поиска в контекст всех шаблонов."""
    return {
        'global_search_form': GlobalSearchForm()
    }