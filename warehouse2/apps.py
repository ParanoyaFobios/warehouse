from django.apps import AppConfig


class Warehouse2Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'warehouse2'
    verbose_name = 'Склад продукции (Products)'

    def ready(self):
        # Импортируем сигналы, чтобы Django о них узнал
        import warehouse2.signals
