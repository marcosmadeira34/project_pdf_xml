from locust import HttpUser, task

class UserBehavior(HttpUser):
    @task
    def envia_nfse(self):
        self.client.post("/login", files={"arquivo": open("uberaba.pdf", "rb")})