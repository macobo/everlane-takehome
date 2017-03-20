import pytest
import simplejson

from cart import cli, schema, query
from click.testing import CliRunner

CLI = cli.cli

@pytest.fixture(scope="module", autouse=True)
def cleanup():
    schema.metadata.drop_all(cli.engine)
    yield
    schema.metadata.drop_all(cli.engine)

def invoke(command, expect_success=True, **kw):
    result = CliRunner().invoke(CLI, command, **kw)
    data = simplejson.loads(result.output.strip())
    assert data['success'] == expect_success
    return data

def test_default_shows_help():
    result = CliRunner().invoke(CLI)
    assert "Shopping cart system for the everlane take-home." in result.output

def test_database_setup():
    invoke(['setup'])

def test_create_cart_command():
    for i in range(1, 4):
        json = invoke(['create_cart'])
        assert json['cart']['id'] == i
        assert json['cart']['state'] == 'active'

def test_show_empty_cart():
    json = invoke(['show_cart', '--cart=1'])
    assert len(json['carts']) == 1

    cart = json['carts'][0]
    assert cart['id'] == 1
    assert cart['state'] == 'active'
    assert cart['total_price'] == 0
    assert cart['products'] == []

def test_show_nonexisting_cart_fails():
    json = invoke(['show_cart', '--cart=123'], expect_success=False)
    assert json['error'] == 'No `cart` with id=123'

def test_add_products():
    result = invoke(['add_product', '--title=first_product', '--price=12.00', '--available_inventory=5'])
    assert result['product'] == {
        'id': 1,
        'title': 'first_product',
        'price': 12.00,
        'available_inventory': 5
    }
    result = invoke(['add_product', '--title=second_product', '--price=1.30', '--available_inventory=10'])
    assert result['product'] == {
        'id': 2,
        'title': 'second_product',
        'price': 1.30,
        'available_inventory': 10
    }

def test_add_product_to_cart():
    invoke(['update_cart', '--cart=1', '--product=2', '--amount=2'])
    invoke(['update_cart', '--cart=2', '--product=2', '--amount=10'])

def test_add_too_much_of_product_to_cart():
    result = invoke(['update_cart', '--cart=1', '--product=1', '--amount=20000'], expect_success=False)
    assert result['error'] == 'Cannot add 20000 of product to cart, only 5 available.'

def test_show_cart_after_add():
    json = invoke(['show_cart', '--cart=1'])
    cart = json['carts'][0]
    assert cart['id'] == 1
    assert cart['state'] == 'active'
    assert cart['total_price'] == 2.6
    assert cart['products'] == [{
        'product_id': 2,
        'title': 'second_product',
        'price': 1.3,
        'amount': 2
    }]

def test_close_cart():
    cart = invoke(['close_cart', '--cart=1'])['cart']
    assert cart['id'] == 1
    assert cart['state'] == 'complete'
    assert cart['total_price'] == 2.6
    assert cart['products'] == [{
        'product_id': 2,
        'title': 'second_product',
        'price': 1.3,
        'amount': 2
    }]

def test_after_close_available_inventory_decreased():
    with cli.engine.begin() as connection:
        product = query.fetchone(connection, schema.products, 2)
        assert product.available_inventory == 8

def test_close_with_not_enough_in_stock():
    "Closing a cart should fail if there's not enough of an item left."
    invoke(['close_cart', '--cart=2'], expect_success=False)

def test_cannot_close_twice():
    json = invoke(['close_cart', '--cart=1'], expect_success=False)
    assert json['error'] == 'Cannot close an inactive cart.'

def test_abort_cart():
    cart = invoke(['close_cart', '--cart=2', '--abort'])['cart']
    assert cart['id'] == 2
    assert cart['state'] == 'aborted'
    assert cart['total_price'] == 13
    assert cart['products'] == [{
        'product_id': 2,
        'title': 'second_product',
        'price': 1.3,
        'amount': 10
    }]

def test_update_cart_update_product_amount():
    invoke(['update_cart', '--cart=3', '--product=2', '--amount=3'])
    cart = invoke(['show_cart', '--cart=3'])['carts'][0]
    assert cart['id'] == 3
    assert cart['state'] == 'active'
    assert cart['total_price'] == 3.9
    assert cart['products'] == [{
        'product_id': 2,
        'title': 'second_product',
        'price': 1.3,
        'amount': 3
    }]

    invoke(['update_cart', '--cart=3', '--product=2', '--amount=4'])
    cart = invoke(['show_cart', '--cart=3'])['carts'][0]
    cart = invoke(['show_cart', '--cart=3'])['carts'][0]
    assert cart['id'] == 3
    assert cart['state'] == 'active'
    assert cart['total_price'] == 5.2
    assert cart['products'] == [{
        'product_id': 2,
        'title': 'second_product',
        'price': 1.3,
        'amount': 4
    }]

def test_remove_from_cart():
    invoke(['update_cart', '--cart=3', '--product=2', '--amount=0'])
    cart = invoke(['show_cart', '--cart=3'])['carts'][0]
    assert cart['id'] == 3
    assert cart['state'] == 'active'
    assert cart['total_price'] == 0
    assert cart['products'] == []
