import pytest
from django.urls import reverse
from usertouser.models import Message, MessageRecipient

@pytest.mark.django_db
class TestUsertouserViews:

    def test_dialogs_list_exclude_self(self, client, user):
        """Проверка, что текущий пользователь не видит себя в списке диалогов"""
        client.login(username='testuser', password='password')
        url = reverse('dialogs')
        
        response = client.get(url)
        # В списке не должно быть 'testuser', так как мы исключаем self в get_dialogs_list
        assert user not in response.context['dialogs_list']

    def test_chat_history_visibility(self, client, user, another_user, direct_message):
        """Проверка отображения истории сообщений в конкретном чате"""
        client.login(username='testuser', password='password')
        url = reverse('chat_detail', kwargs={'user_id': another_user.pk})

        response = client.get(url)
        
        assert response.status_code == 200
        # Проверяем, что сообщение из фикстуры direct_message есть в контексте
        assert direct_message in response.context['chat_history']
        assert "Привет, это тестовое сообщение!" in response.content.decode('utf-8')

    def test_send_message_htmx(self, client, user, another_user):
        """Тест отправки сообщения через HTMX"""
        client.login(username='testuser', password='password')
        url = reverse('chat_detail', kwargs={'user_id': another_user.pk})

        payload = {'content': 'Новое HTMX сообщение'}
        # Имитируем HTMX запрос
        response = client.post(url, payload, HTTP_HX_REQUEST='true')

        assert response.status_code == 200
        # Проверяем, что вернулся только фрагмент списка сообщений
        assert 'message-bubble' in response.content.decode('utf-8')
        assert Message.objects.filter(content='Новое HTMX сообщение').exists()

    def test_delete_chat_removes_from_sidebar(self, client, user, another_user, direct_message):
        """Тест удаления чата: диалог должен исчезнуть из сайдбара"""
        client.login(username='testuser', password='password')
        
        # Сначала проверяем, что another_user есть в списке диалогов
        res_before = client.get(reverse('dialogs'))
        assert another_user in res_before.context['dialogs_list']

        # Выполняем удаление
        delete_url = reverse('delete_chat', kwargs={'user_id': another_user.pk})
        response = client.post(delete_url)

        assert response.status_code == 302 # Редирект обратно в список
        
        # Проверяем список диалогов снова
        res_after = client.get(reverse('dialogs'))
        assert another_user not in res_after.context['dialogs_list']

    def test_soft_delete_logic_database(self, client, user, another_user, direct_message):
        """Проверка, что при удалении устанавливаются правильные флаги в БД"""
        client.login(username='testuser', password='password')
        
        # Создаем также ВХОДЯЩЕЕ сообщение для полноты теста
        incoming_msg = Message.objects.create(sender=another_user, content="Входящее")
        MessageRecipient.objects.create(message=incoming_msg, user=user)

        delete_url = reverse('delete_chat', kwargs={'user_id': another_user.pk})
        client.post(delete_url)

        # 1. Наше исходящее сообщение должно получить флаг sender_deleted
        direct_message.refresh_from_db()
        assert direct_message.sender_deleted is True

        # 2. Входящее сообщение должно получить is_deleted в промежуточной таблице
        recipient_entry = MessageRecipient.objects.get(message=incoming_msg, user=user)
        assert recipient_entry.is_deleted is True

    def test_chat_restores_on_new_message(self, client, user, another_user, direct_message):
        """Тест: удаленный чат должен вернуться в список при получении нового сообщения"""
        client.login(username='testuser', password='password')
        
        # 1. Удаляем чат
        client.post(reverse('delete_chat', kwargs={'user_id': another_user.pk}))
        
        # 2. Имитируем новое сообщение от собеседника (или сами пишем)
        new_msg = Message.objects.create(sender=another_user, content="Я снова тут!")
        MessageRecipient.objects.create(message=new_msg, user=user)

        # 3. Проверяем, появился ли another_user в списке
        response = client.get(reverse('dialogs'))
        assert another_user in response.context['dialogs_list']
        assert response.context['dialogs_list'][0].unread_count == 1

    def test_unread_messages_count_clears_on_open(self, client, user, another_user):
        """Проверка, что сообщения помечаются прочитанными при открытии чата"""
        client.login(username='testuser', password='password')
        
        # Создаем непрочитанное входящее
        msg = Message.objects.create(sender=another_user, content="Секрет")
        recipient = MessageRecipient.objects.create(message=msg, user=user, is_read=False)

        # Открываем чат
        url = reverse('chat_detail', kwargs={'user_id': another_user.pk})
        client.get(url)

        # Проверяем в БД
        recipient.refresh_from_db()
        assert recipient.is_read is True