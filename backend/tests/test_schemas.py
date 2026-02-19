"""Schema tests."""
from app.schemas.common import APIResponse, PaginationMeta, ErrorDetail


def test_api_response_success():
    resp = APIResponse(status="success", data={"id": "123"}, message="OK")
    assert resp.status == "success"
    assert resp.data == {"id": "123"}


def test_api_response_with_pagination():
    pagination = PaginationMeta(total=100, page=1, per_page=20, has_next=True)
    resp = APIResponse(status="success", data=[], pagination=pagination)
    assert resp.pagination is not None
    assert resp.pagination.total == 100
    assert resp.pagination.has_next is True


def test_error_detail():
    err = ErrorDetail(title="Not Found", status=404, detail="User not found")
    assert err.type == "about:blank"
    assert err.status == 404
