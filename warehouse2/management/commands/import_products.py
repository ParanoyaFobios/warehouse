import requests
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from warehouse2.models import Product, ProductCategory
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Импортирует товары из KeyCRM в локальную базу данных с поддержкой S3 и флага архивации.'

    def _fetch_paginated_data(self, session, url):
        page_num = 1
        while url:
            try:
                self.stdout.write(f"  - Запрос страницы: {page_num}...")
                response = session.get(url)
                response.raise_for_status()
                data = response.json()
                yield from data.get('data', [])
                url = data.get('next_page_url')
                page_num += 1
                time.sleep(1.1)
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f'Ошибка при запросе к {url}: {e}'))
                break

    def handle(self, *args, **options):
        API_KEY = getattr(settings, 'KEYCRM_API_KEY', None)
        API_URL = "https://openapi.keycrm.app/v1"

        if not API_KEY:
            self.stdout.write(self.style.ERROR('Не найден KEYCRM_API_KEY в настройках.'))
            return

        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        })

        # --- Шаг 1: Категории ---
        self.stdout.write("Шаг 1: Загрузка категорий...")
        # Сохраняем и ID и Имя
        keycrm_categories = {
            cat['id']: cat['name'] 
            for cat in self._fetch_paginated_data(session, f"{API_URL}/products/categories")
        }
        
        # Обновляем наши категории, сохраняя их KeyCRM ID
        for k_id, k_name in keycrm_categories.items():
            ProductCategory.objects.update_or_create(
                name=k_name,
                defaults={'keycrm_id': k_id} # Убедитесь, что добавили это поле в модель категории
            )

        default_category, _ = ProductCategory.objects.get_or_create(name="Без категории")

        # --- Шаг 2: Товары ---
        self.stdout.write("\nШаг 2: Синхронизация товаров...")
        created_count = 0
        updated_count = 0

        for product_data in self._fetch_paginated_data(session, f"{API_URL}/products"):
            sku = product_data.get('sku')
            if not sku: continue

            keycrm_cat_id = product_data.get('category_id')
            category_obj = default_category
            if keycrm_cat_id and keycrm_cat_id in keycrm_categories:
                category_obj = ProductCategory.objects.filter(name=keycrm_categories[keycrm_cat_id]).first()

            # --- Подготовка данных ---
            defaults = {
                'keycrm_id': product_data.get('id'),
                'name': product_data.get('name', 'Без названия'),
                'price': product_data.get('min_price', 0.00),
                'total_quantity': product_data.get('quantity', 0),
                'category': category_obj,
                'is_archived': product_data.get('is_archived', False), # Обработка архива
                'barcode': product_data.get('barcode') or f"{sku}" # Защита от пустого баркода
            }

            try:
                # Используем SKU как уникальный ключ для сопоставления
                product, created = Product.objects.update_or_create(
                    sku=sku,
                    defaults=defaults
                )

                # --- Обработка изображения ---
                thumbnail_url = product_data.get('thumbnail_url')
                # Загружаем картинку только если:
                # 1. Она есть в KeyCRM
                # 2. У нас в базе ее еще нет ИЛИ мы хотим принудительно обновить (сейчас: только если нет)
                if thumbnail_url and not product.image:
                    try:
                        img_res = requests.get(thumbnail_url, stream=True, timeout=10)
                        img_res.raise_for_status()
                        
                        file_name = f"{sku}_{thumbnail_url.split('/')[-1]}" # Добавляем SKU для уникальности в S3
                        product.image.save(file_name, ContentFile(img_res.content), save=True)
                        self.stdout.write(f"  [img] OK: {product.name}")
                    except Exception as img_e:
                        self.stdout.write(self.style.WARNING(f"  [img] Error {product.name}: {img_e}"))

                if created: created_count += 1
                else: updated_count += 1
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Ошибка SKU {sku}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nГотово! Создано: {created_count}, Обновлено: {updated_count}"))