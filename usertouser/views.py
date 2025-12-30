from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.db.models import Q, Subquery, OuterRef, Count, IntegerField
from django.db.models.functions import Coalesce
from django.contrib.auth import get_user_model

from .models import Message, MessageRecipient
from .forms import NewMessageForm, ChatForm

User = get_user_model()

# Вспомогательная функция для получения списка диалогов (чтобы не дублировать код)
def get_dialogs_list(current_user):
    # Сложное условие: сообщение существует для нас, если:
    # (Мы отправитель и не удалили его) ИЛИ (Мы получатель и не удалили его в Recipient)
    active_messages_query = Message.objects.filter(
        Q(sender=current_user, recipients=OuterRef('pk'), sender_deleted=False) |
        Q(sender=OuterRef('pk'), recipients=current_user, messagerecipient__user=current_user, messagerecipient__is_deleted=False)
    ).order_by('-timestamp').values('timestamp')[:1]

    return User.objects.exclude(pk=current_user.pk).annotate(
        last_msg_date=Subquery(active_messages_query),
        unread_count=Coalesce(
            Subquery(
                MessageRecipient.objects.filter(
                    user=current_user,
                    is_read=False,
                    is_deleted=False,
                    message__sender_id=OuterRef('pk')
                ).values('user').annotate(cnt=Count('pk')).values('cnt'),
                output_field=IntegerField()
            ), 0
        )
    ).filter(
        last_msg_date__isnull=False
    ).order_by('-last_msg_date').prefetch_related('groups')


class CreateDialogView(LoginRequiredMixin, CreateView):
    """
    Экран "Написать новое сообщение" (как кнопка карандаша в Telegram).
    """
    template_name = 'usertouser/create_dialog.html'
    form_class = NewMessageForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # 1. Сохраняем сообщение
        message = form.save(commit=False)
        message.sender = self.request.user
        message.save()
        form.save_m2m() # Сохраняем получателей

        # 2. Логика редиректа. 
        # Если мы написали одному человеку — сразу кидаем в чат с ним.
        recipients = message.recipients.all()
        if recipients.count() == 1:
            return redirect('chat_detail', user_id=recipients.first().pk)
        
        # Если это массовая рассылка (например, всем кладовщикам),
        # то логичнее вернуться в список диалогов.
        return redirect('dialogs') 


class ChatView(LoginRequiredMixin, View):
    """
    Основное окно чата: слева список, справа переписка.
    """
    def get(self, request, user_id=None):
        current_user = request.user
        context = {}
        
        # 1. Список диалогов (для сайдбара)
        context['dialogs_list'] = get_dialogs_list(current_user)

        # Если user_id не передан, мы просто показываем страницу "Выберите чат"
        if not user_id:
            return render(request, 'usertouser/chat_hub.html', context)

        # 2. Активный собеседник
        opponent = get_object_or_404(User, pk=user_id)
        context['opponent'] = opponent
        # 3. Помечаем сообщения как прочитанные
        MessageRecipient.objects.filter(
            user=current_user,
            message__sender=opponent,
            is_read=False
        ).update(is_read=True)

        # 4. История переписки
        context['chat_history'] = Message.objects.filter(
            Q(sender=current_user, recipients=opponent, sender_deleted=False) |
            Q(sender=opponent, recipients=current_user, messagerecipient__user=current_user, messagerecipient__is_deleted=False)
        ).distinct().order_by('timestamp')

        # 5. Форма для ОТВЕТА (Simple/ChatForm)
        context['form'] = ChatForm()
        # Рендерим по-разному в зависимости от того, AJAX это или полный запрос
        if request.headers.get('HX-Request'):
            return render(request, 'usertouser/includes/message_list.html', context)
        
        return render(request, 'usertouser/chat_window.html', context)
    

    def post(self, request, user_id):
            opponent = get_object_or_404(User, pk=user_id)
            form = ChatForm(request.POST)
            
            if form.is_valid():
                message = form.save(commit=False)
                message.sender = request.user
                message.save()
                message.recipients.add(opponent)
                
                # ЕСЛИ ЭТО HTMX (отправка сообщения)
                if request.headers.get('HX-Request'):
                    # Снова получаем историю, чтобы вернуть обновленный список
                    context = {
                        'chat_history': Message.objects.filter(
                            Q(sender=request.user, recipients=opponent) |
                            Q(sender=opponent, recipients=request.user)
                        ).distinct().order_by('timestamp'),
                        'request': request
                    }
                    return render(request, 'usertouser/includes/message_list.html', context)
                
                return redirect('chat_detail', user_id=user_id)
            return self.get(request, user_id)
    

class DeleteChatView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        opponent = get_object_or_404(User, pk=user_id)
        
        # 1. Помечаем сообщения, где мы ПОЛУЧАТЕЛЬ (входящие)
        MessageRecipient.objects.filter(
            user=request.user,
            message__sender=opponent
        ).update(is_deleted=True)
        
        # 2. Помечаем сообщения, где мы ОТПРАВИТЕЛЬ (исходящие)
        Message.objects.filter(
            sender=request.user,
            recipients=opponent
        ).update(sender_deleted=True)
        
        return redirect('dialogs')