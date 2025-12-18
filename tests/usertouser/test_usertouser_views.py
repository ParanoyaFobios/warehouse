import pytest
from django.urls import reverse
from usertouser.models import Message, MessageRecipient
from django.contrib.auth.models import User

@pytest.mark.django_db
class TestMessageSystem:

    # --- ТЕСТЫ ДОСТУПА И ПРИВАТНОСТИ ---

    def test_message_detail_privacy(self, client, user, another_user, direct_message):
        """Пользователь не может видеть чужое сообщение, где он не отправитель и не получатель"""
        # Создаем третьего лишнего
        stranger = User.objects.create_user(username='stranger', password='password')
        client.force_login(stranger)
        
        url = reverse('message_detail', kwargs={'pk': direct_message.pk})
        response = client.get(url)
        
        # Так как в get_queryset стоит фильтр по Q, вернется 404 для постороннего
        assert response.status_code == 404

    def test_inbox_displays_only_my_messages(self, client, user, another_user, direct_message):
        """Входящие показывают только те сообщения, где я — получатель"""
        client.force_login(another_user) # Логинимся как получатель
        
        response = client.get(reverse('inbox'))
        assert response.status_code == 200
        # Проверяем, что сообщение есть во входящих
        assert direct_message in [entry.message for entry in response.context['recipient_entries']]

        # Логинимся как отправитель — во входящих должно быть пусто
        client.force_login(user)
        response = client.get(reverse('inbox'))
        assert len(response.context['recipient_entries']) == 0

    # --- ТЕСТЫ ЛОГИКИ (ПРОЧИТАНО / УДАЛЕНО) ---

    def test_marking_as_read(self, client, another_user, direct_message):
        """Просмотр сообщения получателем меняет статус is_read на True"""
        client.force_login(another_user)
        
        # Сначала проверяем, что не прочитано
        recipient_entry = MessageRecipient.objects.get(message=direct_message, user=another_user)
        assert recipient_entry.is_read is False
        
        # Заходим в детали сообщения
        url = reverse('message_detail', kwargs={'pk': direct_message.pk})
        client.get(url)
        
        # Проверяем, что статус обновился
        recipient_entry.refresh_from_db()
        assert recipient_entry.is_read is True

    def test_inbox_excludes_deleted_messages(self, client, another_user, direct_message):
        """Удаленные сообщения не должны отображаться во входящих"""
        client.force_login(another_user)
        
        # "Удаляем" сообщение для получателя
        MessageRecipient.objects.filter(message=direct_message, user=another_user).update(is_deleted=True)
        
        response = client.get(reverse('inbox'))
        assert len(response.context['recipient_entries']) == 0

    # --- ТЕСТЫ ОТПРАВКИ И ОТВЕТОВ ---

    def test_compose_message_multiple_recipients(self, client, user, another_user):
        """Проверка успешной отправки сообщения нескольким получателям"""
        client.force_login(user)
        user3 = User.objects.create_user(username='user3', password='password')
        
        url = reverse('compose')
        data = {
            'recipients': [another_user.id, user3.id],
            'content': 'Всем привет!'
        }
        
        # Отправляем форму
        response = client.post(url, data)
        
        assert response.status_code == 302 # Редирект в Outbox
        assert Message.objects.filter(content='Всем привет!').count() == 1
        
        msg = Message.objects.get(content='Всем привет!')
        assert msg.recipients.count() == 2

    def test_reply_prefills_recipient(self, client, another_user, direct_message):
        """При ответе на сообщение поле получателя должно быть предзаполнено отправителем оригинала"""
        client.force_login(another_user) # Получатель нажимает "Ответить"
        
        url = reverse('message_reply', kwargs={'pk': direct_message.pk})
        response = client.get(url)
        
        # Проверяем initial данные формы
        # В Django CreateView initial попадает в форму, которую можно вытащить из контекста
        form = response.context['form']
        assert form.initial['recipients'] == [direct_message.sender]