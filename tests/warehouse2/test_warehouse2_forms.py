import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from warehouse2.forms import (ProductForm, ProductIncomingForm, ProductSearchForm,
PackageForm, ShipmentForm, ShipmentItemForm)
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from io import BytesIO


@pytest.mark.django_db
class TestProductForm:
    """Тесты для формы ProductForm"""
    
    def test_product_form_valid_data(self, product_category):
        """Тест валидных данных формы продукта"""
        form_data = {
            'name': 'Тестовый продукт',
            'sku': 'TEST-001',
            'category': product_category.pk,
            'color': 'Красный',
            'price': '1000.50'
        }
        
        form = ProductForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['name'] == 'Тестовый продукт'
        assert form.cleaned_data['sku'] == 'TEST-001'
        assert form.cleaned_data['category'] == product_category
        assert form.cleaned_data['color'] == 'Красный'
        assert form.cleaned_data['price'] == 1000.50
    
    def test_product_form_without_category(self):
        """Тест формы без категории (опциональное поле)"""
        form_data = {
            'name': 'Продукт без категории',
            'sku': 'NO-CAT-001',
            'color': 'Синий',
            'price': '500.00'
        }
        
        form = ProductForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['category'] is None
    
    def test_product_form_without_color(self):
        """Тест формы без цвета (опциональное поле)"""
        form_data = {
            'name': 'Продукт без цвета',
            'sku': 'NO-COLOR-001',
            'price': '500.00'
        }
        
        form = ProductForm(data=form_data)
        assert form.is_valid()
        # Цвет может быть пустым строкой
        assert form.cleaned_data['color'] is None or form.cleaned_data['color'] == ''
    
    def test_product_form_empty_name(self):
        """Тест формы с пустым названием"""
        form_data = {
            'name': '',
            'sku': 'TEST-001',
            'price': '1000'
        }
        
        form = ProductForm(data=form_data)
        assert not form.is_valid()
        assert 'name' in form.errors
    
    def test_product_form_empty_sku(self):
        """Тест формы с пустым артикулом"""
        form_data = {
            'name': 'Тестовый продукт',
            'sku': '',
            'price': '1000'
        }
        
        form = ProductForm(data=form_data)
        assert not form.is_valid()
        assert 'sku' in form.errors
    
    def test_product_form_negative_price(self):
        """Тест формы с отрицательной ценой"""
        form_data = {
            'name': 'Тестовый продукт',
            'sku': 'TEST-001',
            'price': '-100'
        }
        
        form = ProductForm(data=form_data)
        # Форма может принять отрицательную цену, зависит от валидации модели
        # Проверим, что форма валидна (валидация цены происходит на уровне модели)
        assert form.is_valid()
    
    def test_product_form_invalid_price(self):
        """Тест формы с невалидной ценой (не число)"""
        form_data = {
            'name': 'Тестовый продукт',
            'sku': 'TEST-001',
            'price': 'не число'
        }
        
        form = ProductForm(data=form_data)
        assert not form.is_valid()
        assert 'price' in form.errors
    
    def test_product_form_with_image(self, product_category):
        """Тест формы с изображением"""
        # Создаем небольшое валидное изображение в памяти (1x1 пиксель)
        dummy_image = Image.new('RGB', (1, 1))
        image_io = BytesIO()
        # Сохраняем в формате JPEG
        dummy_image.save(image_io, format='jpeg')
        image_io.seek(0) # Сбрасываем указатель

        image = SimpleUploadedFile(
            name='test_image.jpg',
            content=image_io.read(), # <-- Читаем валидный бинарный контент
            content_type='image/jpeg'
        )

        form_data = {
            'name': 'Продукт с изображением',
            'sku': 'IMG-001',
            'price': '1000',
            'category': product_category.pk
        }

        form = ProductForm(data=form_data, files={'image': image})

        # print(form.errors) # Теперь должно быть пусто!
        assert form.is_valid()
    
        # Дополнительные проверки:
        assert 'image' in form.cleaned_data
        assert form.cleaned_data['image'].name == 'test_image.jpg'
    
    def test_product_form_widgets(self):
        """Тест виджетов формы"""
        form = ProductForm()
        
        # Проверяем, что у полей есть правильные CSS классы
        assert 'form-control' in str(form['name'])
        assert 'form-control' in str(form['sku'])
        assert 'form-control' in str(form['color'])
        assert 'form-control' in str(form['price'])
        assert 'form-control' in str(form['image'])
        
        # Проверяем атрибуты полей
        assert 'step="0.01"' in str(form['price'])
    
    def test_product_form_fields(self):
        """Тест полей формы"""
        form = ProductForm()
        
        # Проверяем, что только нужные поля присутствуют
        expected_fields = ['name', 'sku', 'category', 'color', 'price', 'image']
        assert list(form.fields.keys()) == expected_fields
        
        # Проверяем, что поля total_quantity и reserved_quantity отсутствуют
        assert 'total_quantity' not in form.fields
        assert 'reserved_quantity' not in form.fields
        assert 'barcode' not in form.fields


@pytest.mark.django_db
class TestProductIncomingForm:
    """Тесты для формы ProductIncomingForm"""
    
    def test_product_incoming_form_valid_data(self, product):
        """Тест валидных данных формы оприходования"""
        form_data = {
            'product': str(product.pk),
            'quantity': '50',
            'comment': 'Оприходование от поставщика'
        }
        
        form = ProductIncomingForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['product'] == product.pk
        assert form.cleaned_data['quantity'] == 50
        assert form.cleaned_data['comment'] == 'Оприходование от поставщика'
    
    def test_product_incoming_form_without_comment(self, product):
        """Тест формы с пустым комментарием (опциональное поле)"""
        form_data = {
            'product': str(product.pk),
            'quantity': '50',
            'comment': ''
        }
        
        form = ProductIncomingForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['comment'] == ''
    
    def test_product_incoming_form_min_quantity(self, product):
        """Тест формы с минимальным количеством (1)"""
        form_data = {
            'product': str(product.pk),
            'quantity': '1',
            'comment': 'Минимальное количество'
        }
        
        form = ProductIncomingForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['quantity'] == 1
    
    def test_product_incoming_form_zero_quantity(self, product):
        """Тест формы с нулевым количеством"""
        form_data = {
            'product': str(product.pk),
            'quantity': '0',
            'comment': 'Тест'
        }
        
        form = ProductIncomingForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_product_incoming_form_negative_quantity(self, product):
        """Тест формы с отрицательным количеством"""
        form_data = {
            'product': str(product.pk),
            'quantity': '-10',
            'comment': 'Тест'
        }
        
        form = ProductIncomingForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_product_incoming_form_invalid_product_id(self):
        """Тест формы с несуществующим ID продукта"""
        form_data = {
            'product': '9999',  # Несуществующий ID
            'quantity': '50',
            'comment': 'Тест'
        }
        
        form = ProductIncomingForm(data=form_data)
        # Форма должна быть валидной, так как проверка существования продукта
        # происходит во view, а не в форме
        assert form.is_valid()
    
    def test_product_incoming_form_invalid_quantity_type(self, product):
        """Тест формы с нечисловым количеством"""
        form_data = {
            'product': str(product.pk),
            'quantity': 'не число',
            'comment': 'Тест'
        }
        
        form = ProductIncomingForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_product_incoming_form_widgets(self):
        """Тест виджетов формы"""
        form = ProductIncomingForm()
        
        # Проверяем, что поле product скрытое
        assert 'type="hidden"' in str(form['product'])
        
        # Проверяем, что у полей есть правильные CSS классы
        assert 'form-control' in str(form['quantity'])
        assert 'form-control' in str(form['comment'])
        
        # Проверяем атрибуты полей
        assert 'placeholder="Введите количество"' in str(form['quantity'])
        assert 'placeholder="Введите комментарий"' not in str(form['comment'])  # У комментария нет плейсхолдера в коде
    
    def test_product_incoming_form_labels(self):
        """Тест меток полей формы"""
        form = ProductIncomingForm()
        
        assert form.fields['quantity'].label == "Количество к поступлению"
        assert form.fields['comment'].label == "Комментарий (номер накладной, поставщик и т.д.)"


@pytest.mark.django_db
class TestProductSearchForm:
    """Тесты для формы ProductSearchForm"""
    
    def test_product_search_form_valid_data(self):
        """Тест валидных данных формы поиска"""
        form_data = {
            'barcode': '123456789012',
            'name': 'Тестовый продукт',
            'sku': 'TEST-001'
        }
        
        form = ProductSearchForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['barcode'] == '123456789012'
        assert form.cleaned_data['name'] == 'Тестовый продукт'
        assert form.cleaned_data['sku'] == 'TEST-001'
    
    def test_product_search_form_partial_data(self):
        """Тест формы с частичными данными"""
        # Только штрихкод
        form_data = {'barcode': '123456789012'}
        form = ProductSearchForm(data=form_data)
        assert form.is_valid()
        
        # Только название
        form_data = {'name': 'Тестовый продукт'}
        form = ProductSearchForm(data=form_data)
        assert form.is_valid()
        
        # Только артикул
        form_data = {'sku': 'TEST-001'}
        form = ProductSearchForm(data=form_data)
        assert form.is_valid()
    
    def test_product_search_form_empty_data(self):
        """Тест формы с пустыми данными (все поля опциональны)"""
        form_data = {}
        form = ProductSearchForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['barcode'] == ''
        assert form.cleaned_data['name'] == ''
        assert form.cleaned_data['sku'] == ''
    
    def test_product_search_form_whitespace_data(self):
        """Тест формы с пробелами"""
        form_data = {
            'barcode': '   ',
            'name': '  ',
            'sku': ' '
        }
        
        form = ProductSearchForm(data=form_data)
        assert form.is_valid()
        # Пробелы должны быть обрезаны
        assert form.cleaned_data['barcode'] == ''
        assert form.cleaned_data['name'] == ''
        assert form.cleaned_data['sku'] == ''
    
    def test_product_search_form_long_barcode(self):
        """Тест формы с длинным штрихкодом"""
        form_data = {
            'barcode': '12345678901234567890'  # 20 символов
        }
        
        form = ProductSearchForm(data=form_data)
        assert not form.is_valid()
        assert 'barcode' in form.errors
    
    def test_product_search_form_widgets(self):
        """Тест виджетов формы"""
        form = ProductSearchForm()
        
        # Проверяем плейсхолдеры
        assert 'placeholder="Введите штрихкод"' in str(form['barcode'])
        assert 'placeholder="Введите название"' in str(form['name'])
        assert 'placeholder="Введите артикул"' in str(form['sku'])
    
    def test_product_search_form_labels(self):
        """Тест меток полей формы"""
        form = ProductSearchForm()
        
        assert form.fields['barcode'].label == 'Штрихкод'
        assert form.fields['name'].label == 'Название'
        assert form.fields['sku'].label == 'Артикул'


@pytest.mark.django_db
class TestPackageForm:
    """Тесты для формы PackageForm"""
    
    def test_package_form_valid_data(self):
        """Тест валидных данных формы упаковки"""
        form_data = {
            'name': 'Тестовая упаковка',
            'quantity': '10'
        }
        
        form = PackageForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['name'] == 'Тестовая упаковка'
        assert form.cleaned_data['quantity'] == 10
    
    def test_package_form_without_name(self):
        """Тест формы без названия (опциональное поле)"""
        form_data = {
            'name': '',
            'sku': 'TEST-001',
            'category': 'Test_Category',
            'quantity': '10'
        }
        
        form = PackageForm(data=form_data)
        assert not form.is_valid()
        assert 'name' in form.errors
    
    def test_package_form_min_quantity(self):
        """Тест формы с минимальным количеством (1)"""
        form_data = {
            'name': 'Упаковка',
            'quantity': '1'
        }
        
        form = PackageForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['quantity'] == 1
    
    def test_package_form_zero_quantity(self):
        """Тест формы с нулевым количеством"""
        form_data = {
            'name': 'Упаковка',
            'quantity': '0'
        }
        
        form = PackageForm(data=form_data)
        # PositiveIntegerField не допускает 0 по умолчанию
        # Но в форме используется NumberInput без явного min_value
        # Проверим поведение
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_package_form_negative_quantity(self):
        """Тест формы с отрицательным количеством"""
        form_data = {
            'name': 'Упаковка',
            'quantity': '-5'
        }
        
        form = PackageForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_package_form_large_quantity(self):
        """Тест формы с большим количеством"""
        form_data = {
            'name': 'Большая упаковка',
            'quantity': '1000000'
        }
        
        form = PackageForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['quantity'] == 1000000
    
    def test_package_form_invalid_quantity_type(self):
        """Тест формы с нечисловым количеством"""
        form_data = {
            'name': 'Упаковка',
            'quantity': 'не число'
        }
        
        form = PackageForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_package_form_widgets(self):
        """Тест виджетов формы"""
        form = PackageForm()
        
        # Проверяем CSS классы
        assert 'form-control' in str(form['name'])
        assert 'form-control' in str(form['quantity'])
        
        # Проверяем плейсхолдеры
        assert 'placeholder="Например, пак (10)"' in str(form['name'])
        assert 'placeholder="Кол-во штук в упаковке"' in str(form['quantity'])
    
    def test_package_form_labels(self):
        """Тест меток полей формы"""
        form = PackageForm()
        
        assert form.fields['name'].label == 'Название упаковки'
        assert form.fields['quantity'].label == 'Количество'
    
    def test_package_form_fields(self):
        """Тест полей формы"""
        form = PackageForm()
        
        # Проверяем, что только нужные поля присутствуют
        expected_fields = ['name', 'quantity']
        assert list(form.fields.keys()) == expected_fields
        
        # Проверяем, что поле product отсутствует (устанавливается в view)
        assert 'product' not in form.fields
        assert 'barcode' not in form.fields


@pytest.mark.django_db
class TestShipmentForm:
    """Тесты для формы ShipmentForm"""
    
    def test_shipment_form_valid_data(self, sender):
        """Тест валидных данных формы отгрузки"""
        form_data = {
            'sender': sender.pk,
            'destination': 'ул. Тестовая, 123',
            'recipient': 'ООО Получатель'
        }
        
        form = ShipmentForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['sender'] == sender
        assert form.cleaned_data['destination'] == 'ул. Тестовая, 123'
        assert form.cleaned_data['recipient'] == 'ООО Получатель'
    
    def test_shipment_form_without_sender(self):
        """Тест формы без отправителя (опциональное поле)"""
        form_data = {
            'destination': 'ул. Тестовая, 123',
            'recipient': 'ООО Получатель'
        }
        
        form = ShipmentForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['sender'] is None
    
    def test_shipment_form_without_destination(self):
        """Тест формы без адреса (опциональное поле)"""
        form_data = {
            'sender': '',  # Пустая строка вместо None
            'recipient': 'ООО Получатель'
        }
        
        form = ShipmentForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['destination'] == ''
    
    def test_shipment_form_without_recipient(self):
        """Тест формы без получателя (опциональное поле)"""
        form_data = {
            'sender': '',
            'destination': 'ул. Тестовая, 123'
        }
        
        form = ShipmentForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['recipient'] == None
    
    def test_shipment_form_all_empty(self):
        """Тест формы со всеми пустыми полями"""
        form_data = {}
        
        form = ShipmentForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['sender'] is None
        assert form.cleaned_data['destination'] == ''
        assert form.cleaned_data['recipient'] == None
    
    def test_shipment_form_invalid_sender_id(self):
        """Тест формы с несуществующим отправителем"""
        form_data = {
            'sender': '9999',  # Несуществующий ID
            'destination': 'ул. Тестовая, 123',
            'recipient': 'ООО Получатель'
        }
        
        form = ShipmentForm(data=form_data)
        # Форма должна быть валидной, валидация происходит при сохранении
        assert not form.is_valid()
        assert 'sender' in form.errors
        

    
    def test_shipment_form_widgets(self):
        """Тест виджетов формы"""
        form = ShipmentForm()
        
        # Проверяем CSS классы
        assert 'form-select' in str(form['sender'])
        assert 'form-control' in str(form['destination'])
        assert 'form-control' in str(form['recipient'])
        
        # Проверяем плейсхолдеры
        assert 'placeholder="ФОП (отправитель)"' in str(form['sender'])
        assert 'placeholder="Город, адрес склада и т.д."' in str(form['destination'])
        assert 'placeholder="Получатель (Ф.И.О. или название компании)"' in str(form['recipient'])
    
    def test_shipment_form_labels(self):
        """Тест меток полей формы"""
        form = ShipmentForm()
        
        assert form.fields['sender'].label == 'ФОП (отправитель)'
        assert form.fields['destination'].label == 'Пункт назначения'
        assert form.fields['recipient'].label == 'Получатель (Ф.И.О.)'
    
    def test_shipment_form_fields(self):
        """Тест полей формы"""
        form = ShipmentForm()
        
        # Проверяем, что только нужные поля присутствуют
        expected_fields = ['sender', 'destination', 'recipient']
        assert list(form.fields.keys()) == expected_fields
        
        # Проверяем, что поля created_by, processed_by, status отсутствуют
        assert 'created_by' not in form.fields
        assert 'processed_by' not in form.fields
        assert 'status' not in form.fields
        assert 'created_at' not in form.fields
        assert 'shipped_at' not in form.fields


@pytest.mark.django_db
class TestShipmentItemForm:
    """Тесты для формы ShipmentItemForm"""
    
    def test_shipment_item_form_valid_data(self):
        """Тест валидных данных формы позиции отгрузки"""
        form_data = {
            'item_identifier': 'product-1',
            'quantity': '5'
        }
        
        form = ShipmentItemForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['item_identifier'] == 'product-1'
        assert form.cleaned_data['quantity'] == 5
    
    def test_shipment_item_form_package_identifier(self):
        """Тест формы с идентификатором упаковки"""
        form_data = {
            'item_identifier': 'package-5',
            'quantity': '2'
        }
        
        form = ShipmentItemForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['item_identifier'] == 'package-5'
        assert form.cleaned_data['quantity'] == 2
    
    def test_shipment_item_form_min_quantity(self):
        """Тест формы с минимальным количеством (1)"""
        form_data = {
            'item_identifier': 'product-1',
            'quantity': '1'
        }
        
        form = ShipmentItemForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['quantity'] == 1
    
    def test_shipment_item_form_zero_quantity(self):
        """Тест формы с нулевым количеством"""
        form_data = {
            'item_identifier': 'product-1',
            'quantity': '0'
        }
        
        form = ShipmentItemForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_shipment_item_form_negative_quantity(self):
        """Тест формы с отрицательным количеством"""
        form_data = {
            'item_identifier': 'product-1',
            'quantity': '-5'
        }
        
        form = ShipmentItemForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_shipment_item_form_empty_identifier(self):
        """Тест формы с пустым идентификатором"""
        form_data = {
            'item_identifier': '',
            'quantity': '5'
        }
        
        form = ShipmentItemForm(data=form_data)
        assert not form.is_valid()
        assert 'item_identifier' in form.errors
    
    def test_shipment_item_form_missing_identifier(self):
        """Тест формы без идентификатора"""
        form_data = {
            'quantity': '5'
        }
        
        form = ShipmentItemForm(data=form_data)
        assert not form.is_valid()
        assert 'item_identifier' in form.errors
    
    def test_shipment_item_form_missing_quantity(self):
        """Тест формы без количества"""
        form_data = {
            'item_identifier': 'product-1'
        }
        
        form = ShipmentItemForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_shipment_item_form_invalid_quantity_type(self):
        """Тест формы с нечисловым количеством"""
        form_data = {
            'item_identifier': 'product-1',
            'quantity': 'не число'
        }
        
        form = ShipmentItemForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_shipment_item_form_invalid_identifier_format(self):
        """Тест формы с неверным форматом идентификатора"""
        # Некорректный формат (без тире)
        form_data = {
            'item_identifier': 'product1',
            'quantity': '5'
        }
        
        form = ShipmentItemForm(data=form_data)
        # Форма должна быть валидной, валидация формата происходит во view
        assert form.is_valid()
    
    def test_shipment_item_form_widgets(self):
        """Тест виджетов формы"""
        form = ShipmentItemForm()
        
        # Проверяем, что поле item_identifier скрытое
        assert 'type="hidden"' in str(form['item_identifier'])
        
        # Проверяем CSS классы
        assert 'form-control' in str(form['quantity'])
        
        # Проверяем атрибуты
        assert 'value="1"' in str(form['quantity'])  # Значение по умолчанию
    
    def test_shipment_item_form_labels(self):
        """Тест меток полей формы"""
        form = ShipmentItemForm()
        
        assert form.fields['quantity'].label == "Количество"
        # У скрытого поля item_identifier обычно нет метки
        assert form.fields['item_identifier'].label is None or form.fields['item_identifier'].label == ''
    
    def test_shipment_item_form_fields(self):
        """Тест полей формы"""
        form = ShipmentItemForm()
        
        # Проверяем, что только нужные поля присутствуют
        expected_fields = ['item_identifier', 'quantity', 'price_override']
        assert list(form.fields.keys()) == expected_fields


@pytest.mark.django_db
class TestFormsEdgeCases:
    """Тесты для граничных случаев форм"""
    
    def test_product_form_very_long_name(self):
        """Тест формы продукта с очень длинным названием"""
        long_name = 'Очень длинное название продукта, которое превышает обычную длину, но должно быть обработано корректно ' * 5
        
        form_data = {
            'name': long_name[:200],  # Ограничение 200 символов
            'sku': 'LONG-001',
            'price': '1000'
        }
        
        form = ProductForm(data=form_data)
        assert form.is_valid()
    
    def test_product_form_special_characters(self):
        """Тест формы продукта со специальными символами"""
        form_data = {
            'name': 'Продукт ©®™±≠≤≥≈∞',
            'sku': 'SPECIAL-001',
            'color': 'Цвет с символами: ©®™',
            'price': '1000'
        }
        
        form = ProductForm(data=form_data)
        assert form.is_valid()
    
    def test_package_form_decimal_quantity(self):
        """Тест формы упаковки с десятичным количеством"""
        form_data = {
            'name': 'Упаковка',
            'quantity': '10.5'  # Дробное количество
        }
        
        form = PackageForm(data=form_data)
        # PositiveIntegerField не принимает дроби
        assert not form.is_valid()
        assert 'quantity' in form.errors
    
    def test_shipment_form_very_long_destination(self):
        """Тест формы отгрузки с очень длинным адресом"""
        long_destination = 'Очень длинный адрес доставки, который содержит много информации о месте назначения, включая город, улицу, дом, квартиру и дополнительные указания ' * 5
        
        form_data = {
            'destination': long_destination[:255],  # Ограничение 255 символов
            'recipient': 'Получатель'
        }
        
        form = ShipmentForm(data=form_data)
        assert form.is_valid()
    
    def test_product_incoming_form_large_quantity(self):
        """Тест формы оприходования с очень большим количеством"""
        form_data = {
            'product': '1',
            'quantity': '999999',
            'comment': 'Большая партия'
        }
        
        form = ProductIncomingForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['quantity'] == 999999