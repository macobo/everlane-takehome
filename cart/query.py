import schema
import utils
import sqlalchemy

from itertools import groupby
from sqlalchemy.sql import text
from sqlalchemy.dialects.postgresql import insert

def fetchone(connection, table, id, lock_for_update = False):
    """
    Returns a single row for `table` with given id.

    If no such row is found, an error is raised.
    If `lock_for_update` is True, the row is locked.
    """
    query = table \
        .select() \
        .where(table.c.id == id)

    if lock_for_update:
        query = query.with_for_update()
    result = connection.execute(query).fetchone()

    if result is None:
        raise ValueError("No row in `{}` with id={}".format(table.name, id))
    return result

def delete(connection, table, ids):
    "Deletes existing row from `connection`, returning it (or none)."
    query = table \
        .delete() \

    for name, value in ids.items():
        query = query.where(table.c[name] == value)

    query = query.returning(*table.columns)
    return connection.execute(query).fetchone()

def upsert(connection, table, id_keys, update):
    """
    Upserts a row to `table` with the given primary key(s).
    """
    values = dict(id_keys)
    values.update(update)
    upsert_query = insert(table) \
        .values(**values) \
        .on_conflict_do_update(index_elements=id_keys.keys(), set_=update)

    return connection.execute(upsert_query)

def update_cart(connection, id, **values):
    listing_update = schema.cart \
        .update() \
        .values(values) \
        .where(schema.cart.c.id == id)
    connection.execute(listing_update)

def _get_cart_contents(connection, cart_ids):
    """
    For each `cart` in cart_ids, this returns a Dictionary from id -> List(product_row)
    """
    result_columns = [
        schema.cart_contents.c.cart_id,
        schema.cart_contents.c.product_id,
        schema.cart_contents.c.amount,
        schema.products.c.title,
        schema.products.c.price
    ]

    products_query = sqlalchemy.select(result_columns) \
        .select_from(schema.cart_contents.join(schema.products)) \
        .where(schema.cart_contents.c.cart_id.in_(cart_ids)) \
        .where(schema.cart_contents.c.product_id == schema.products.c.id) \
        .order_by(schema.products.c.title)
    products = connection.execute(products_query).fetchall()
    # Group results by cart id
    product_groups = groupby(products, key=lambda p: p.cart_id)
    return {cart_id: list(products) for cart_id, products in product_groups}

def summarize_cart(cart, products):
    total_price = sum(p.price * p.amount for p in products)
    return {
        'id': cart.id,
        'created_at': str(cart.created_at),
        'state': schema.CartState.to_string(cart.state),
        'products': utils.proxy_to_dict(products, omit_keys={'cart_id'}),
        'total_price': total_price
    }

def cart_info(connection, cart_ids):
    "Returns a list of dictionaries containing basic information about each cart."
    cart_query = schema.cart \
        .select() \
        .where(schema.cart.c.id.in_(cart_ids)) \
        .with_for_update() # lock results to avoid someone closing the cart in a race.
    carts = {cart.id: cart for cart in connection.execute(cart_query)}
    contents = _get_cart_contents(connection, cart_ids)

    result = []
    for cart_id in cart_ids:
        if cart_id not in carts:
            raise ValueError("No `cart` with id={}".format(cart_id))
        products = contents.get(cart_id, [])
        result.append(summarize_cart(carts[cart_id], products))
    return result

def decrement_cart_product_availability(connection, cart_id):
    """
    For each product in cart with `cart_id`, this decrements the availability
    of each item by the amount it's in cart.

    Will raise an error if available_inventory would dip below zero.
    """
    statement = text("""
        UPDATE products
        SET available_inventory = available_inventory - cart_contents.amount
        FROM cart_contents
        WHERE products.id = cart_contents.product_id
          AND cart_contents.cart_id = :cart_id
    """)
    connection.execute(statement, cart_id=cart_id)
