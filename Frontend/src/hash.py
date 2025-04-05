import bcrypt

password = b"BrikliCto"
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode())