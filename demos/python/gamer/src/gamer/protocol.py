from pydantic import BaseModel


class GameInfo(BaseModel):
    id: str
    name: str
