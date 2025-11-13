from typing import Any, Iterable

from django.core.paginator import Paginator


def apply_pagination(items: Iterable[Any], request, page_size: int | None = None, default_page_size: int = 20):
    """
    统一分页封装：根据请求参数获取 page，并对 items 进行分页。

    - 保持与现有视图逻辑一致：从 querystring 读取 'page'，page_size 由调用方决定；
    - 若未传入 page_size，则使用 default_page_size；
    - 返回 Paginator 的 Page 对象，便于模板复用 page_obj 接口。
    """
    page = request.GET.get('page', 1)
    size = page_size or default_page_size
    paginator = Paginator(items, size)
    return paginator.get_page(page)

