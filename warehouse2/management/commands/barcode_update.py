import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from warehouse2.models import Product

class Command(BaseCommand):
    help = 'Генерирует новые уникальные штрихкоды для всех товаров только в локальной БД'

    def generate_local_barcode(self):
        """Локальная копия логики генерации для надежности скрипта"""
        return uuid.uuid4().hex[:15].upper()

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Запуск массового обновления штрихкодов...'))
        
        products = Product.objects.all()
        total = products.count()
        updated_count = 0

        # Используем транзакцию для ускорения процесса
        with transaction.atomic():
            for product in products:
                # Генерируем новый штрихкод
                new_barcode = self.generate_local_barcode()
                
                # Проверяем на уникальность (на всякий случай)
                while Product.objects.filter(barcode=new_barcode).exists():
                    new_barcode = self.generate_local_barcode()

                # Обновляем через .filter().update() 
                # Это работает быстрее и ГАРАНТИРОВАННО не вызывает сигналы Django
                Product.objects.filter(pk=product.pk).update(barcode=new_barcode)
                
                updated_count += 1
                
                if updated_count % 50 == 0:
                    self.stdout.write(f'Обработано: {updated_count}/{total}')

        self.stdout.write(self.style.SUCCESS(
            f'Готово! Обновлено товаров: {updated_count}. Сигналы не вызывались.'
        ))