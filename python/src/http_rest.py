from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str


class NewUser(BaseModel):
    name: str


app = FastAPI()
users: dict[int, User] = {}


@app.get("/users")
def list_users() -> list[User]:
    return list(users.values())


@app.get("/users/{user_id}")
def get_user(user_id: int) -> User:
    if user := users.get(user_id):
        return user
    raise HTTPException(404)


@app.post("/users", status_code=201)
def create_user(body: NewUser) -> User:
    user = User(id=len(users) + 1, name=body.name)
    users[user.id] = user
    return user


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3000)
