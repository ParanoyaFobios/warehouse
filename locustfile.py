import json
from locust import HttpUser, task, between

class WarehouseUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Метод вызывается при старте каждого пользователя"""
        # 1. Сначала заходим на страницу логина, чтобы получить CSRF-токен в куки
        response = self.client.get("/admin/login/") # или твой путь к логину
        csrftoken = response.cookies.get('csrftoken')

        # 2. Логинимся (используем полученный токен)
        # Если у тебя кастомный логин, замени путь
        self.client.post("/admin/login/", {
            "username": "root", # Убедись, что такой юзер есть в БД!
            "password": "0880",
            "csrfmiddlewaretoken": csrftoken
        }, headers={"Referer": f"{self.host}/admin/login/"})

    @task(3)
    def view_workorders(self):

        self.client.get("/production/workorders/")

    @task(1)
    def report_production(self):
        # Достаем токен из кук для AJAX запроса
        csrftoken = self.client.cookies.get('csrftoken')
        
        payload = {
            "workorder_id": 2, # Твой существующий ID
            "quantity": 1
        }
        
        self.client.post("/production/api/workorder/report/", 
            data=json.dumps(payload),
            headers={
                "X-CSRFToken": csrftoken,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json"
            }
        )

    @task(2)
    def view_portfolio(self):
        self.client.get("/production/portfolio/")