from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


# -----------------------------
# Password Test
# -----------------------------

password = "TestPassword123"

hashed = hash_password(password)

print("Password verification:")
print("Correct:", verify_password(password, hashed))
print("Wrong:", verify_password("WrongPassword", hashed))


# -----------------------------
# JWT Test
# -----------------------------

data = {
    "sub": "1",
    "role": "STUDENT",
}

token = create_access_token(data)

print("\nJWT:")
print(token)

decoded = decode_access_token(token)

print("\nDecoded JWT:")
print(decoded)