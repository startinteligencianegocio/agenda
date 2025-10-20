import bcrypt

senha = "AnaClara2017@!"
senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())

print(senha_hash.decode("utf-8"))