import pydantic


class ItemListMeta(pydantic.BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class ItemList[T](pydantic.BaseModel):
    items: list[T]
    meta: ItemListMeta
