"""OpenAPI documentation: schema is served, valid, complete and honest about auth."""
import pytest
from django.urls import Resolver404, resolve
from drf_spectacular.validation import validate_schema

pytestmark = pytest.mark.django_db

EXPECTED_OPERATIONS = {
    ("/api/health/", "get"),
    ("/api/auth/register/", "post"),
    ("/api/auth/login/", "post"),
    ("/api/auth/refresh/", "post"),
    ("/api/auth/me/", "get"),
    ("/api/categories/", "get"), ("/api/categories/", "post"),
    ("/api/categories/{id}/", "get"), ("/api/categories/{id}/", "put"),
    ("/api/categories/{id}/", "patch"), ("/api/categories/{id}/", "delete"),
    ("/api/products/", "get"), ("/api/products/", "post"),
    ("/api/products/{id}/", "get"), ("/api/products/{id}/", "put"),
    ("/api/products/{id}/", "patch"), ("/api/products/{id}/", "delete"),
    ("/api/cart/", "get"), ("/api/cart/", "delete"),
    ("/api/cart/items/", "post"),
    ("/api/cart/items/{id}/", "patch"), ("/api/cart/items/{id}/", "delete"),
    ("/api/orders/", "get"), ("/api/orders/{id}/", "get"),
    ("/api/orders/checkout/", "post"),
}
JWT = {"jwtAuth": []}


@pytest.fixture
def schema(api_client):
    res = api_client.get("/api/schema/")
    assert res.status_code == 200
    return res.json()


def operations(schema):
    return {(path, method) for path, ops in schema["paths"].items() for method in ops}


def test_schema_is_public_json_and_valid_openapi(api_client, schema):
    res = api_client.get("/api/schema/")
    assert res["Content-Type"].startswith("application/vnd.oai.openapi+json")
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "MiniCommerce API"
    assert schema["info"]["version"] == "1.0.0"
    validate_schema(schema)  # raises on an invalid OpenAPI document


@pytest.mark.parametrize("url,marker", [("/api/docs/", "swagger-ui"), ("/api/redoc/", "redoc")])
def test_ui_pages_load(api_client, url, marker):
    res = api_client.get(url)
    assert res.status_code == 200
    assert marker in res.content.decode().lower()


def test_documents_exactly_the_real_endpoints(schema):
    assert operations(schema) == EXPECTED_OPERATIONS


def test_every_documented_path_resolves_to_a_real_view(schema):
    for path in schema["paths"]:
        try:
            resolve(path.replace("{id}", "1"))
        except Resolver404:  # pragma: no cover - failure message is the point
            pytest.fail(f"Documented path does not exist: {path}")


def test_jwt_bearer_security_scheme(schema):
    assert schema["components"]["securitySchemes"]["jwtAuth"] == {
        "type": "http", "scheme": "bearer", "bearerFormat": "JWT",
    }


@pytest.mark.parametrize("path,method", [
    ("/api/auth/me/", "get"), ("/api/cart/", "get"), ("/api/cart/items/", "post"),
    ("/api/orders/", "get"), ("/api/orders/checkout/", "post"),
    ("/api/products/", "post"), ("/api/categories/{id}/", "delete"),
])
def test_protected_endpoints_require_jwt(schema, path, method):
    assert schema["paths"][path][method]["security"] == [JWT]  # no anonymous `{}` option


@pytest.mark.parametrize("path,method", [
    ("/api/products/", "get"), ("/api/products/{id}/", "get"),
    ("/api/categories/", "get"), ("/api/health/", "get"), ("/api/auth/register/", "post"),
])
def test_public_endpoints_allow_anonymous(schema, path, method):
    assert {} in schema["paths"][path][method]["security"]


def test_login_is_public_and_returns_token_pair(schema):
    op = schema["paths"]["/api/auth/login/"]["post"]
    assert "security" not in op or {} in op["security"]
    assert set(schema["components"]["schemas"]["TokenObtainPair"]["properties"]) == {"access", "refresh"}
    assert {"200", "401", "429"} <= set(op["responses"])


def test_product_list_query_parameters(schema):
    params = {p["name"]: p for p in schema["paths"]["/api/products/"]["get"]["parameters"]}
    assert set(params) >= {"category", "is_active", "min_price", "max_price", "search", "ordering", "page", "page_size"}
    assert "-price" in params["ordering"]["schema"]["enum"]
    response = schema["paths"]["/api/products/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["$ref"].endswith("/PaginatedProductList")


def test_product_request_and_response_schemas_differ(schema):
    components = schema["components"]["schemas"]
    assert "category_id" in components["ProductRequest"]["properties"]   # write: id
    assert "category" in components["Product"]["properties"]             # read: nested object
    assert "category_id" not in components["Product"]["properties"]


def test_checkout_documented_without_body_and_with_errors(schema):
    op = schema["paths"]["/api/orders/checkout/"]["post"]
    assert "requestBody" not in op
    assert op["responses"]["201"]["content"]["application/json"]["schema"]["$ref"].endswith("/OrderDetail")
    assert {"400", "401"} <= set(op["responses"])


def test_password_is_never_in_a_response_schema(schema):
    components = schema["components"]["schemas"]
    assert "password" not in components["Register"]["properties"]
    assert "password" not in components["User"]["properties"]
    assert "password" in components["RegisterRequest"]["properties"]
