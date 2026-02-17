import pytest
from django.urls import reverse
from django.contrib.auth.models import User, Group, Permission
from main.models import UserProfile
from warehouse1.models import Material
from warehouse2.models import Product

@pytest.mark.django_db
class TestUserManagement:
    """Тесты управления пользователями (создание, ред., удаление)"""

    def test_user_list_view_permission(self, client, user):
        """Проверка доступа к списку пользователей"""
        url = reverse('user_list')
        
        # Без прав — редирект на логин или 403
        client.force_login(user)
        response = client.get(url)
        assert response.status_code == 403 

        # Даем права
        perm = Permission.objects.get(codename='view_user')
        user.user_permissions.add(perm)
        response = client.get(url)
        assert response.status_code == 200

    def test_create_user_with_profile_and_group(self, client, staff_user):
        """Тест создания пользователя через CreateUserWithGroupView"""
        # Даем админу право на добавление
        perm = Permission.objects.get(codename='add_user')
        staff_user.user_permissions.add(perm)
        client.force_login(staff_user)

        group = Group.objects.create(name="Менеджеры")
        url = reverse('create_user')
        data = {
            'username': 'new_worker',
            'password': 'password123',
            'password2': 'password123',
            'first_name': 'Иван',
            'phone': '123456789',
            'group': group.id
        }

        response = client.post(url, data)
        assert response.status_code == 302 # Редирект после успеха
        
        new_user = User.objects.get(username='new_worker')
        assert new_user.first_name == 'Иван'
        assert new_user.groups.filter(name="Менеджеры").exists()
        assert new_user.profile.phone == '123456789'

    def test_user_safe_delete(self, client, staff_user, user):
        """Мягкое удаление пользователя (is_active = False)"""
        perm = Permission.objects.get(codename='delete_user')
        staff_user.user_permissions.add(perm)
        client.force_login(staff_user)

        url = reverse('delete_user', kwargs={'pk': user.pk})
        response = client.get(url)
        
        user.refresh_from_db()
        assert response.status_code == 302
        assert user.is_active is False

@pytest.mark.django_db
class TestGlobalSearch:
    """Тесты глобального поиска"""

    def test_search_redirect_to_material(self, client, user, material):
        """Если найден только материал — редирект в склад 1"""
        client.force_login(user)
        url = f"{reverse('global_search')}?q={material.name}"
        response = client.get(url)
        
        # Проверяем, что редирект ведет на список материалов с параметром поиска
        assert response.status_code == 302
        assert reverse('material_list') in response.url

    def test_search_ambiguous_results(self, client, user, material, product):
        """Если найдено и там, и там — показываем страницу выбора"""
        client.force_login(user)
        # Делаем имена одинаковыми для теста
        material.name = "УникальныйОбъект"
        material.save()
        product.name = "УникальныйОбъект"
        product.save()

        url = f"{reverse('global_search')}?q=УникальныйОбъект"
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'search_results.html' in [t.name for t in response.templates]

@pytest.mark.django_db
class TestUtilityViews:
    """Тесты профиля"""

    def test_user_profile_signal_behavior(self, user):
        """Проверяем, что UserProfile работает корректно при создании User"""
        # Твоя вьюха использует update_or_create, проверим модель
        profile, created = UserProfile.objects.get_or_create(user=user, defaults={'phone': '777'})
        assert profile.user.username == 'testuser'