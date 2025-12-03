import pytest
import io
from decimal import Decimal
from PIL import Image
from django.urls import reverse
from warehouse1.models import Material, MaterialCategory, MaterialOperation, MaterialColor, UnitOfMeasure
from warehouse1.forms import MaterialForm


class TestMaterialListView:
    """Тесты для списка материалов"""
    
    @pytest.mark.django_db
    def test_get_list_view_authenticated(self, client, user, material):
        """Тест GET-запроса страницы списка материалов для аутентифицированного пользователя"""
        client.force_login(user)
        url = reverse('material_list')
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'materials' in response.context
        assert 'categories' in response.context
        assert material in response.context['materials']
        assert 'warehouse1/material_list.html' in [t.name for t in response.templates]
        
        # Проверяем пагинацию
        assert 'paginator' in response.context
    
    @pytest.mark.django_db
    def test_get_list_view_unauthenticated(self, client):
        """Тест GET-запроса без авторизации (должен перенаправить на логин)"""
        url = reverse('material_list')
        
        response = client.get(url)
        
        assert response.status_code == 302
        assert 'login/' in response.url
    
    @pytest.mark.django_db
    def test_filter_by_category(self, client, user, material_category, material):
        """Тест фильтрации по категории"""
        client.force_login(user)
        url = reverse('material_list')
        
        # Создаем материал в другой категории
        category2 = MaterialCategory.objects.create(name="Другая категория")
        material2 = Material.objects.create(
            name="Другой материал",
            article="OTHER-001",
            category=category2,
            quantity=50,
            unit=material.unit
        )
        
        # Фильтруем по первой категории
        response = client.get(url, {'category': material_category.pk})
        
        assert response.status_code == 200
        materials = list(response.context['materials'])
        assert material in materials
        assert material2 not in materials
    
    @pytest.mark.django_db
    def test_search_by_name(self, client, user, material):
        """Тест поиска по названию"""
        client.force_login(user)
        url = reverse('material_list')
        
        response = client.get(url, {'search': material.name})
        
        assert response.status_code == 200
        assert material in response.context['materials']
    
    @pytest.mark.django_db
    def test_search_by_article(self, client, user, material):
        """Тест поиска по артикулу"""
        client.force_login(user)
        url = reverse('material_list')
        
        response = client.get(url, {'search': material.article})
        
        assert response.status_code == 200
        assert material in response.context['materials']
    
    @pytest.mark.django_db
    def test_search_by_barcode(self, client, user, material):
        """Тест поиска по штрихкоду"""
        client.force_login(user)
        url = reverse('material_list')
        
        response = client.get(url, {'search': material.barcode})
        
        assert response.status_code == 200
        assert material in response.context['materials']
    
    @pytest.mark.django_db
    def test_empty_search(self, client, user, material):
        """Тест пустого поиска (должен вернуть все материалы)"""
        client.force_login(user)
        url = reverse('material_list')
        
        response = client.get(url, {'search': ''})
        
        assert response.status_code == 200
        assert material in response.context['materials']
    
    @pytest.mark.django_db
    def test_multiple_search_terms(self, client, user, material):
        """Тест поиска с несколькими терминами"""
        client.force_login(user)
        url = reverse('material_list')
        
        # Создаем второй материал для теста
        material2 = Material.objects.create(
            name="Поисковый тест",
            article="SEARCH-001",
            category=material.category,
            quantity=30,
            unit=material.unit
        )
        
        # Поиск по части имени
        response = client.get(url, {'search': 'тест'})
        
        assert response.status_code == 200
        assert material2 in response.context['materials']


class TestMaterialCreateView:
    """Тесты для создания материала"""
    
    @pytest.mark.django_db
    def test_get_create_view_authenticated(self, client, user):
        """Тест GET-запроса страницы создания материала"""
        client.force_login(user)
        url = reverse('material_create')
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert isinstance(response.context['form'], MaterialForm)
        assert 'warehouse1/material_form.html' in [t.name for t in response.templates]
    
    @pytest.mark.django_db
    def test_get_create_view_unauthenticated(self, client):
        """Тест GET-запроса без авторизации"""
        url = reverse('material_create')
        
        response = client.get(url)
        
        assert response.status_code == 302
        assert 'login/' in response.url
    
    @pytest.mark.django_db
    def test_post_create_view_valid_data(self, client, user, material_category, unit_of_measure, material_color):
        """Тест успешного создания материала с валидными данными."""
        client.force_login(user)
        url = reverse('material_create')
        
        post_data = {
            'name': 'Новый тестовый материал',
            'article': 'NEW-TEST-001',
            'category': material_category.pk,
            'min_quantity': '10.00',
            'color': material_color.pk,
            'unit': unit_of_measure.pk,
            'description': 'Описание нового материала'
        }
        
        response = client.post(url, post_data, follow=True)
        
        # Проверяем редирект на список материалов
        assert response.status_code == 200
        assert response.redirect_chain[-1][0] == reverse('material_list')
        
        # Проверяем что материал создан
        material = Material.objects.filter(article='NEW-TEST-001').first()
        assert material is not None
        assert material.name == 'Новый тестовый материал'
        
        # Количество должно быть 0, как того требует бизнес-логика
        assert material.quantity == Decimal('0.00') 
        # assert material.quantity == material.default # более надежная проверка
    
    @pytest.mark.django_db
    def test_post_create_view_without_color(self, client, user, material_category, unit_of_measure):
        """Тест создания материала без указания цвета (опциональное поле)"""
        client.force_login(user)
        url = reverse('material_create')
        
        post_data = {
            'name': 'Материал без цвета',
            'article': 'NO-COLOR-001',
            'category': material_category.pk,
            'quantity': '0',
            'min_quantity': '0',
            'unit': unit_of_measure.pk,
            'description': 'Материал без указания цвета'
        }
        
        response = client.post(url, post_data, follow=True)
        
        assert response.status_code == 200
        material = Material.objects.filter(article='NO-COLOR-001').first()
        assert material is not None
        assert material.color is None
    
    @pytest.mark.django_db
    def test_post_create_view_duplicate_article(self, client, user, material):
        """Тест создания материала с дублирующимся артикулом (должна быть ошибка)"""
        client.force_login(user)
        url = reverse('material_create')
        
        post_data = {
            'name': 'Дубликат материала',
            'article': material.article,  # Используем существующий артикул
            'category': material.category.pk,
            'quantity': '50',
            'unit': material.unit.pk
        }
        
        response = client.post(url, post_data)
        
        # Должна вернуться форма с ошибкой
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors
    
    @pytest.mark.django_db
    def test_post_create_view_invalid_data(self, client, user):
        """Тест создания материала с невалидными данными"""
        client.force_login(user)
        url = reverse('material_create')
        
        post_data = {
            'name': '',  # Пустое имя - недопустимо
            'article': '',
            'quantity': '-10'  # Отрицательное количество
        }
        
        response = client.post(url, post_data)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors


class TestMaterialBarcodeView:
    """Тесты для генерации штрихкода"""
    
    @pytest.mark.django_db
    def test_barcode_view_authenticated(self, client, user, material):
        """Тест GET-запроса страницы штрихкода для аутентифицированного пользователя"""
        client.force_login(user)
        url = reverse('material_barcode', kwargs={'pk': material.pk})
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Проверяем что возвращается валидное изображение
        image_data = io.BytesIO(response.content)
        img = Image.open(image_data)
        assert img.format == 'PNG'
        
        # Проверяем размер изображения
        assert img.width > 0
        assert img.height > 0
    
    
    @pytest.mark.django_db
    def test_barcode_view_nonexistent_material(self, client, user):
        """Тест запроса штрихкода для несуществующего материала"""
        client.force_login(user)
        url = reverse('material_barcode', kwargs={'pk': 9999})
        
        response = client.get(url)
        
        assert response.status_code == 404
    
    @pytest.mark.django_db
    def test_barcode_content(self, client, user, material):
        """Тест содержимого штрихкода (базовые проверки)"""
        client.force_login(user)
        url = reverse('material_barcode', kwargs={'pk': material.pk})
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert len(response.content) > 0  # Должны быть какие-то данные


class TestMaterialDetailView:
    """Тесты для детального просмотра материала"""
    
    @pytest.mark.django_db
    def test_get_detail_view_authenticated(self, client, user, material):
        """Тест GET-запроса детальной страницы материала"""
        client.force_login(user)
        url = reverse('material_detail', kwargs={'pk': material.pk})
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'material' in response.context
        assert response.context['material'] == material
        assert 'operations' in response.context
        assert 'barcode_img' in response.context
        assert 'warehouse1/material_detail.html' in [t.name for t in response.templates]
        
        # Проверяем что barcode_img содержит HTML img тег
        assert 'img' in response.context['barcode_img']
        assert 'src=' in response.context['barcode_img']
    
    @pytest.mark.django_db
    def test_get_detail_view_unauthenticated(self, client, material):
        """Тест GET-запроса без авторизации"""
        url = reverse('material_detail', kwargs={'pk': material.pk})
        
        response = client.get(url)
        
        assert response.status_code == 302
        assert 'login/' in response.url
    
    @pytest.mark.django_db
    def test_get_detail_view_nonexistent_material(self, client, user):
        """Тест запроса несуществующего материала"""
        client.force_login(user)
        url = reverse('material_detail', kwargs={'pk': 9999})
        
        response = client.get(url)
        
        assert response.status_code == 404
    
    @pytest.mark.django_db
    def test_detail_view_with_operations(self, client, user, material):
        """Тест детальной страницы с историей операций"""
        client.force_login(user)
        
        # Создаем несколько операций для материала
        for i in range(5):
            MaterialOperation.objects.create(
                material=material,
                operation_type='incoming',
                quantity=10 * (i + 1),
                user=user,
                comment=f'Тестовая операция {i+1}'
            )
        
        url = reverse('material_detail', kwargs={'pk': material.pk})
        response = client.get(url)
        
        assert response.status_code == 200
        operations = response.context['operations']
        assert operations.count() <= 15  # Ограничение по [:15]
        assert operations.count() == 5
        
        # Проверяем порядок (должен быть по убыванию даты)
        dates = [op.date for op in operations]
        assert dates == sorted(dates, reverse=True)
    
    @pytest.mark.django_db
    def test_detail_view_operations_limit(self, client, user, material):
        """Тест ограничения количества операций (15 последних)"""
        client.force_login(user)
        
        # Создаем больше 15 операций
        for i in range(20):
            MaterialOperation.objects.create(
                material=material,
                operation_type='incoming',
                quantity=5,
                user=user,
                comment=f'Операция {i+1}'
            )
        
        url = reverse('material_detail', kwargs={'pk': material.pk})
        response = client.get(url)
        
        assert response.status_code == 200
        operations = response.context['operations']
        assert operations.count() == 15  # Ограничение [:15]


class TestMaterialUpdateView:
    """Тесты для обновления материала"""
    
    @pytest.mark.django_db
    def test_get_update_view_authenticated(self, client, user, material):
        """Тест GET-запроса страницы обновления материала"""
        client.force_login(user)
        url = reverse('material_update', kwargs={'pk': material.pk})
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert isinstance(response.context['form'], MaterialForm)
        assert response.context['form'].instance == material
        assert 'warehouse1/material_form.html' in [t.name for t in response.templates]
    
    @pytest.mark.django_db
    def test_get_update_view_unauthenticated(self, client, material):
        """Тест GET-запроса без авторизации"""
        url = reverse('material_update', kwargs={'pk': material.pk})
        
        response = client.get(url)
        
        assert response.status_code == 302
        assert 'login/' in response.url
    
    @pytest.mark.django_db
    def test_get_update_view_nonexistent_material(self, client, user):
        """Тест запроса обновления несуществующего материала"""
        client.force_login(user)
        url = reverse('material_update', kwargs={'pk': 9999})
        
        response = client.get(url)
        
        assert response.status_code == 404
    
    @pytest.mark.django_db
    def test_post_update_view_valid_data(self, client, user, material):
        """Тест успешного обновления материала"""
        client.force_login(user)
        url = reverse('material_update', kwargs={'pk': material.pk})
        
        post_data = {
            'name': 'Обновленное название',
            'article': material.article,  # Тот же артикул
            'category': material.category.pk,
            'quantity': material.quantity,
            'min_quantity': material.min_quantity,
            'color': material.color.pk if material.color else '',
            'unit': material.unit.pk,
            'description': 'Обновленное описание материала'
        }
        
        response = client.post(url, post_data, follow=True)
        
        # Проверяем редирект на список материалов
        assert response.status_code == 200
        assert response.redirect_chain[-1][0] == reverse('material_list')
        
        # Проверяем обновление материала
        material.refresh_from_db()
        assert material.name == 'Обновленное название'
        assert material.quantity == Decimal('100.00')
        assert material.min_quantity == Decimal('10.00')
        assert material.description == 'Обновленное описание материала'
    
    @pytest.mark.django_db
    def test_post_update_view_change_article_duplicate(self, client, user, material):
        """Тест обновления с изменением артикула на существующий (должна быть ошибка)"""
        # Создаем второй материал
        material2 = Material.objects.create(
            name='Второй материал',
            article='SECOND-001',
            category=material.category,
            quantity=50,
            unit=material.unit
        )
        
        client.force_login(user)
        url = reverse('material_update', kwargs={'pk': material.pk})
        
        # Пытаемся изменить артикул первого материала на артикул второго
        post_data = {
            'name': material.name,
            'article': material2.article,  # Дублирующий артикул
            'category': material.category.pk,
            'quantity': str(material.quantity),
            'unit': material.unit.pk
        }
        
        response = client.post(url, post_data)
        
        # Должна вернуться форма с ошибкой
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors
    
    @pytest.mark.django_db
    def test_post_update_view_keep_same_article(self, client, user, material):
        """Тест обновления с сохранением того же артикула (должно пройти успешно)"""
        client.force_login(user)
        url = reverse('material_update', kwargs={'pk': material.pk})
        
        post_data = {
            'name': 'Новое имя, тот же артикул',
            'article': material.article,  # Сохраняем тот же артикул
            'category': material.category.pk,
            'quantity': str(material.quantity),
            'min_quantity': str(material.min_quantity),
            'unit': material.unit.pk
        }
        
        response = client.post(url, post_data, follow=True)
        
        # Должно пройти успешно (тот же артикул разрешен)
        assert response.status_code == 200
        material.refresh_from_db()
        assert material.name == 'Новое имя, тот же артикул'
    
    @pytest.mark.django_db
    def test_post_update_view_remove_color(self, client, user, material):
        """Тест обновления с удалением цвета"""
        # Сначала убедимся что у материала есть цвет
        if material.color is None:
            color = MaterialColor.objects.create(name="Тестовый цвет")
            material.color = color
            material.save()
        
        client.force_login(user)
        url = reverse('material_update', kwargs={'pk': material.pk})
        
        post_data = {
            'name': material.name,
            'article': material.article,
            'category': material.category.pk,
            'quantity': str(material.quantity),
            'min_quantity': str(material.min_quantity),
            'color': '',  # Пустое значение - удаляем цвет
            'unit': material.unit.pk,
            'description': material.description
        }
        
        response = client.post(url, post_data, follow=True)
        
        assert response.status_code == 200
        material.refresh_from_db()
        assert material.color is None
    
    @pytest.mark.django_db
    def test_post_update_view_invalid_quantity(self, client, user, material):
        """Тест обновления с невалидным количеством"""
        client.force_login(user)
        url = reverse('material_update', kwargs={'pk': material.pk})
        
        post_data = {
            'name': material.name,
            'article': material.article,
            'category': material.category.pk,
            'quantity': '-100',  # Отрицательное количество
            'unit': material.unit.pk
        }
        
        response = client.post(url, post_data)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors


class TestMaterialViewsPermissions:
    """Тесты для проверки прав доступа"""
    
    @pytest.mark.django_db
    def test_permission_can_view_material_quantity(self, client, user, material):
        """Тест разрешения на просмотр количества материалов"""
        client.force_login(user)
        url = reverse('material_detail', kwargs={'pk': material.pk})
        
        response = client.get(url)
        
        # Проверяем что количество отображается
        assert response.status_code == 200
        # В шаблоне должно быть отображено количество
        # Для простоты проверяем что контекст содержит материал с quantity
        assert hasattr(response.context['material'], 'quantity')
        assert response.context['material'].quantity is not None


class TestMaterialViewsEdgeCases:
    """Тесты для граничных случаев представлений"""
    
    @pytest.mark.django_db
    def test_material_list_pagination(self, client, user, material_category, unit_of_measure):
        """Тест пагинации списка материалов"""
        # Создаем больше материалов чем paginate_by (20)
        for i in range(25):
            Material.objects.create(
                name=f'Материал для пагинации {i+1}',
                article=f'PAGINATION-{i+1:03d}',
                category=material_category,
                quantity=10 * (i + 1),
                unit=unit_of_measure
            )
        
        client.force_login(user)
        url = reverse('material_list')
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'paginator' in response.context
        assert 'page_obj' in response.context
        
        # Проверяем что пагинация работает
        paginator = response.context['paginator']
        assert paginator.num_pages > 1
        assert paginator.count == Material.objects.count()
        
        # Проверяем количество на странице
        assert len(response.context['materials']) == 20  # paginate_by = 20
    
    @pytest.mark.django_db
    def test_material_list_empty(self, client, user):
        """Тест пустого списка материалов"""
        # Удаляем все материалы
        Material.objects.all().delete()
        
        client.force_login(user)
        url = reverse('material_list')
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'materials' in response.context
        assert response.context['materials'].count() == 0
    
    @pytest.mark.django_db
    def test_material_detail_no_operations(self, client, user, material):
        """Тест детальной страницы материала без операций"""
        client.force_login(user)
        
        # Удаляем все операции для материала
        MaterialOperation.objects.filter(material=material).delete()
        
        url = reverse('material_detail', kwargs={'pk': material.pk})
        response = client.get(url)
        
        assert response.status_code == 200
        operations = response.context['operations']
        assert operations.count() == 0
    
    @pytest.mark.django_db
    def test_material_barcode_large_name(self, client, user):
        """Тест генерации штрихкода для материала с длинным названием"""
        # Создаем материал с очень длинным названием
        material_category = MaterialCategory.objects.create(name="Тест категория")
        unit_of_measure = UnitOfMeasure.objects.create(name="Штука", short_name="шт")
        
        long_name = "Очень длинное название материала, которое может не поместиться в одну строку и должно корректно обрабатываться при генерации штрихкода"
        
        material = Material.objects.create(
            name=long_name,
            article="LONG-NAME-001",
            category=material_category,
            quantity=100,
            unit=unit_of_measure
        )
        
        client.force_login(user)
        url = reverse('material_barcode', kwargs={'pk': material.pk})
        
        response = client.get(url)
        
        # Проверяем что генерация прошла успешно
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Проверяем что изображение создано
        image_data = io.BytesIO(response.content)
        img = Image.open(image_data)
        assert img.format == 'PNG'
        assert img.width > 0
        assert img.height > 0
    
    @pytest.mark.django_db
    def test_material_create_with_special_characters(self, client, user, material_category, unit_of_measure):
        """Тест создания материала со специальными символами в названии"""
        client.force_login(user)
        url = reverse('material_create')
        
        post_data = {
            'name': 'Материал со спецсимволами: ©®™±≠≤≥≈∞',
            'article': 'SPECIAL-001',
            'category': material_category.pk,
            'quantity': '50',
            'min_quantity': '5',
            'unit': unit_of_measure.pk
        }
        
        response = client.post(url, post_data, follow=True)
        
        assert response.status_code == 200
        material = Material.objects.filter(article='SPECIAL-001').first()
        assert material is not None
        assert material.name == 'Материал со спецсимволами: ©®™±≠≤≥≈∞'