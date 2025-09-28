from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from .models import Message, MessageRecipient
from .forms import MessageForm

class InboxView(LoginRequiredMixin, ListView):
    template_name = 'usertouser/inbox.html'
    context_object_name = 'recipient_entries' # Переименовали для ясности

    def get_queryset(self):
        # Теперь мы ищем не сообщения, а записи в MessageRecipient
        return MessageRecipient.objects.filter(
            user=self.request.user, 
            is_deleted=False
        ).select_related('message', 'message__sender').order_by('-message__timestamp')

# OutboxView остается почти без изменений
class OutboxView(LoginRequiredMixin, ListView):
    template_name = 'usertouser/outbox.html'
    context_object_name = 'sent_messages'
    
    def get_queryset(self):
        return Message.objects.filter(
            sender=self.request.user,
            sender_deleted=False
        )

class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    template_name = 'usertouser/message_detail.html'
    context_object_name = 'message'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        message = self.get_object()
        # Помечаем сообщение как прочитанное для ТЕКУЩЕГО пользователя
        MessageRecipient.objects.filter(
            message=message,
            user=self.request.user
        ).update(is_read=True)
        return context

class ComposeMessageView(LoginRequiredMixin, CreateView):
    form_class = MessageForm
    template_name = 'usertouser/message_form.html'
    success_url = reverse_lazy('outbox')

    def form_valid(self, form):
        # Создаем одно "тело" сообщения
        message = form.save(commit=False)
        message.sender = self.request.user
        message.save()
        # form.save_m2m() # Это нужно для ManyToManyField, если бы мы не использовали through
        
        # А теперь создаем записи в промежуточной таблице для каждого получателя
        recipients = form.cleaned_data['recipients']
        for recipient in recipients:
            MessageRecipient.objects.create(
                message=message,
                user=recipient
            )
        
        return super(CreateView, self).form_valid(form)