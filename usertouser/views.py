from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages as django_messages
from .models import Message, MessageRecipient
from .forms import MessageForm
from django.db import models




class InboxView(LoginRequiredMixin, ListView):
    template_name = 'usertouser/inbox.html'
    context_object_name = 'recipient_entries'

    def get_queryset(self):
        return MessageRecipient.objects.filter(
            user=self.request.user, 
            is_deleted=False
        ).select_related('message', 'message__sender').order_by('-message__timestamp')

class OutboxView(LoginRequiredMixin, ListView):
    template_name = 'usertouser/outbox.html'
    context_object_name = 'sent_messages'
    
    def get_queryset(self):
        return Message.objects.filter(
            sender=self.request.user,
            sender_deleted=False
        ).prefetch_related('recipients')

class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    template_name = 'usertouser/message_detail.html'
    context_object_name = 'message'

    def get_queryset(self):
        # Пользователь может видеть сообщение если он отправитель или получатель
        return Message.objects.filter(
            models.Q(sender=self.request.user) |
            models.Q(messagerecipient__user=self.request.user)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        message = self.get_object()
        
        # Помечаем как прочитанное только если пользователь получатель
        if message.sender != self.request.user:
            MessageRecipient.objects.filter(
                message=message,
                user=self.request.user
            ).update(is_read=True)
        
        return context

class ComposeMessageView(LoginRequiredMixin, CreateView):
    form_class = MessageForm
    template_name = 'usertouser/message_form.html'
    success_url = reverse_lazy('outbox')

    def get_form_kwargs(self):
        """Передает текущего пользователя в конструктор формы."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user # Передаем request.user в форму
        return kwargs
    
    def get_initial(self):
        """
        Предзаполняет форму данными для ответа, если это ответ на сообщение.
        """
        initial = super().get_initial()
        # Получаем pk исходного сообщения из URL
        reply_to_pk = self.kwargs.get('pk')
        
        if reply_to_pk:
            original_message = get_object_or_404(Message, pk=reply_to_pk)
            # Проверяем, что текущий пользователь - один из получателей
            if self.request.user in original_message.recipients.all():
                # Предзаполняем получателя (это отправитель исходного письма)
                initial['recipients'] = [original_message.sender]        
        return initial

    def form_valid(self, form):
        """
        Обрабатывает отправку формы: создает одно сообщение
        и связывает его с выбранными получателями.
        """
        try:
            # 1. Создаем объект сообщения, но пока не сохраняем в БД
            message = form.save(commit=False)
            message.sender = self.request.user
            # Сохраняем основное сообщение
            message.save()
            
            # 2. Теперь, когда у message есть ID, добавляем получателей
            # form.save_m2m() автоматически создаст записи в промежуточной таблице
            form.save_m2m()

            recipients_count = form.cleaned_data['recipients'].count()
            django_messages.success(self.request, f'Сообщение успешно отправлено {recipients_count} получателям.')
        except Exception as e:
            django_messages.error(self.request, f'Ошибка при отправке сообщения: {str(e)}')
            return self.form_invalid(form)

        # После всех операций вручную делаем редирект
        return super().form_valid(form)