from schemas.auth import RegisterRequest, LoginRequest


register = RegisterRequest(
    email="student@example.com",
    password="TestPassword123",
    role="STUDENT",
    full_name="Test Student",
)

print("Registration schema:")
print(register)

login = LoginRequest(
    email="student@example.com",
    password="TestPassword123",
)

print("\nLogin schema:")
print(login)