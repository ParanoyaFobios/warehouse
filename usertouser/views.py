from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from .models import Message
from .forms import MessageForm
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.auth.decorators import login_required


class InboxView(LoginRequiredMixin, ListView):
    template_name = 'usertouser/inbox.html'
    context_object_name = 'messages'

    def get_queryset(self):
        # Показываем только полученные и не удаленные получателем сообщения
        return Message.objects.filter(
            recipient=self.request.user, 
            recipient_deleted=False
        )

class OutboxView(LoginRequiredMixin, ListView):
    template_name = 'usertouser/outbox.html'
    context_object_name = 'messages'

    def get_queryset(self):
        # Показываем только отправленные и не удаленные отправителем сообщения
        return Message.objects.filter(
            sender=self.request.user, 
            sender_deleted=False
        )

class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    template_name = 'usertouser/message_detail.html'
    context_object_name = 'message'

    def get_object(self, queryset=None):
        # Получаем объект сообщения
        message = super().get_object(queryset)
        # Если текущий пользователь - получатель и сообщение не прочитано,
        # помечаем его как прочитанное
        if self.request.user == message.recipient and not message.is_read:
            message.is_read = True
            message.save()
        return message

class ComposeMessageView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = 'usertouser/message_form.html'
    success_url = reverse_lazy('outbox') # После отправки переходим в исходящие

    def get_initial(self):
        # Эта функция предзаполняет форму, идеально для ответа
        initial = super().get_initial()
        reply_to_pk = self.kwargs.get('pk')
        if reply_to_pk:
            original_message = get_object_or_404(Message, pk=reply_to_pk)
            # Убедимся, что можно отвечать
            if original_message.recipient == self.request.user:
                initial['recipient'] = original_message.sender
                
        return initial

    def form_valid(self, form):
        # Перед сохранением формы, указываем, что отправитель - это текущий пользователь
        form.instance.sender = self.request.user
        return super().form_valid(form)
    

@login_required
def user_search_json(request):
    query = request.GET.get('q', '').strip()
    results = []
    if len(query) >= 2:
        # Ищем по имени пользователя, имени или фамилии
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(pk=request.user.pk).distinct()[:10] # Исключаем себя из поиска

        for user in users:
            results.append({
                'id': user.id,
                'name': user.get_full_name() or user.username
            })
    return JsonResponse({'results': results})