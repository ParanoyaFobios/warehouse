import requests
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from warehouse2.models import Product, ProductCategory
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Импортирует товары из KeyCRM в локальную базу данных, обрабатывая пагинацию и rate limits.'

    def _fetch_paginated_data(self, session, url):
        """
        Вспомогательная функция для получения всех данных с пагинированных эндпоинтов.
        """
        page_num = 1
        while url:
            try:
                self.stdout.write(f"  - Запрос страницы: {page_num}...")
                response = session.get(url)
                response.raise_for_status()
                data = response.json()
                
                # yield from - элегантно отдает каждый элемент из списка
                yield from data.get('data', [])

                url = data.get('next_page_url')
                page_num += 1
                
                # Уважаем ограничение API в 60 запросов/минуту
                time.sleep(1.1)

            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f'Ошибка при запросе к {url}: {e}'))
                break

    def handle(self, *args, **options):
        API_KEY = getattr(settings, 'KEYCRM_API_KEY', None)
        API_URL = "https://openapi.keycrm.app/v1"

        if not API_KEY:
            self.stdout.write(self.style.ERROR('Не найден KEYCRM_API_KEY в настройках проекта.'))
            return

        # Используем сессию для переиспользования соединения и заголовков
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        })

        # --- Шаг 1: Загрузка ВСЕХ категорий ---
        self.stdout.write("Шаг 1: Загрузка категорий из KeyCRM...")
        keycrm_categories = {
            cat['id']: cat['name'] 
            for cat in self._fetch_paginated_data(session, f"{API_URL}/products/categories")
        }
        self.stdout.write(self.style.SUCCESS(f"Загружено {len(keycrm_categories)} категорий."))

        # Создаем или находим категорию по умолчанию
        default_category, _ = ProductCategory.objects.get_or_create(name="Без категории")

        # --- Шаг 2: Загрузка и обработка ВСЕХ товаров ---
        self.stdout.write("\nШаг 2: Загрузка и синхронизация товаров...")
        created_count = 0
        updated_count = 0

        all_products_generator = self._fetch_paginated_data(session, f"{API_URL}/products")

        for product_data in all_products_generator:
            sku = product_data.get('sku')
            if not sku:
                self.stdout.write(self.style.WARNING(f"Пропущен товар '{product_data.get('name')}' без артикула (SKU)."))
                continue

            # --- ИСПРАВЛЕННАЯ ЛОГИКА ОБРАБОТКИ КАТЕГОРИИ ---
            category_obj = default_category # По умолчанию
            keycrm_cat_id = product_data.get('category_id')
            if keycrm_cat_id and keycrm_cat_id in keycrm_categories:
                category_name = keycrm_categories[keycrm_cat_id]
                # Находим или создаем категорию в нашей БД
                category_obj, _ = ProductCategory.objects.get_or_create(name=category_name)
            
            # --- Сопоставление полей ---
            defaults = {
                'name': product_data.get('name', 'Без названия'),
                'price': product_data.get('min_price', 0.00),
                'total_quantity': product_data.get('quantity', 0),
                'category': category_obj, # Теперь здесь никогда не будет None
            }

            try:
                product, created = Product.objects.update_or_create(
                    sku=sku,
                    defaults=defaults
                )
                # --- 👇 НОВЫЙ БЛОК: ЗАГРУЗКА ИЗОБРАЖЕНИЯ 👇 ---
                thumbnail_url = product_data.get('thumbnail_url')
                # Загружаем, только если есть URL и у товара еще нет изображения
                if thumbnail_url and not product.image:
                    try:
                        img_response = requests.get(thumbnail_url, stream=True)
                        img_response.raise_for_status()
                        
                        # Получаем имя файла из URL
                        file_name = thumbnail_url.split('/')[-1]
                        
                        # Создаем Django-совместимый файл из скачанного контента
                        django_file = ContentFile(img_response.content)
                        
                        # Сохраняем файл в ImageField
                        product.image.save(file_name, django_file, save=True)
                        self.stdout.write(f"  [img] Загружено изображение для {product.name}")

                    except requests.exceptions.RequestException as img_e:
                        self.stdout.write(self.style.WARNING(f"  [!] Не удалось загрузить изображение для {product.name}: {img_e}"))

                if created:
                    created_count += 1
                else:
                    updated_count += 1
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Не удалось сохранить товар с SKU {sku}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nСинхронизация завершена! Создано: {created_count}, Обновлено: {updated_count}."
        ))