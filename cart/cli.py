import click
import query
import schema
import utils

from sqlalchemy import create_engine
from utils import json_output

engine = create_engine('postgresql://localhost', echo=False)

@click.group()
def cli():
    """
    Shopping cart system for the everlane take-home.

    \b
    To see specific subcommand help, invoke it as such:
    $ ./cart.py add_product --help
    """

@cli.command()
@json_output
def setup():
    "Sets up the local pg database"
    schema.metadata.create_all(engine)
    return {'dbUrl': str(engine.url)}

@cli.command()
@json_output
def create_cart():
    "Creates a new, empty shopping cart"
    insert_statement = schema.cart \
        .insert() \
        .values(state=schema.CartState.ACTIVE) \
        .returning(*schema.cart.columns)
    cart = engine.connect().execute(insert_statement).fetchone()

    return {
        'cart': {
            'id': cart.id,
            'state': schema.CartState.to_string(cart.state),
            'created_at': str(cart.created_at)
        }
    }

@cli.command()
@utils.option('--title', 'Title of the product')
@utils.option('--price', 'Price of the product', type=float)
@utils.option('--available_inventory', 'How many of the product is available', type=click.IntRange(min=0))
@json_output
def add_product(title, price, available_inventory):
    "Adds a product to list of available products"
    if price < 0.01:
        raise ValueError("Price of the product must be at least 1 cent.")

    insert_statement = schema.products \
        .insert() \
        .values(title=title, price=price, available_inventory=available_inventory) \
        .returning(*schema.products.columns)
    with engine.begin() as connection:
        product = connection.execute(insert_statement)
    return {'product': utils.proxy_to_dict(product)[0]}

@cli.command()
@utils.option('--cart', 'Id of the shopping cart', type=int)
@utils.option('--product', 'Id of product to add to cart', type=int)
@utils.option('--amount', 'How many to add to cart (0 to remove)', default=1, required=False, type=click.IntRange(min=0))
@json_output
def update_cart(cart, product, amount):
    "Adds or removes items from an existing cart"
    with engine.begin() as connection:
        product_row = query.fetchone(connection, schema.products, product, lock_for_update=True)
        if product_row.available_inventory < amount:
            raise ValueError("Cannot add {} of product to cart, only {} available.".format(amount, product_row.available_inventory))

        cart_row = query.fetchone(connection, schema.cart, cart, lock_for_update=True)
        if cart_row.state != schema.CartState.ACTIVE:
            raise ValueError("Cannot update a not active cart.")

        # Upsert the new item to cart. If a row already exists, this _overwrites_ the old value.
        key = {'product_id': product, 'cart_id': cart}
        if amount == 0:
            query.delete(connection, schema.cart_contents, key)
        else:
            query.upsert(connection, schema.cart_contents, key, {'amount': amount})
    return {}

@cli.command()
@utils.option('--cart', 'Shopping cart ids', multiple=True, type=int)
@json_output
def show_cart(cart):
    "Shows the state of one or many shopping carts"
    with engine.begin() as connection:
        return {'carts': query.cart_info(connection, cart)}

@cli.command()
@utils.option('--cart', 'Id of the shopping cart', type=int)
@utils.option('--abort', 'Set the cart as aborted', required=False, is_flag=True, prompt=False)
@json_output
def close_cart(cart, abort):
    "Purchases or aborts a cart"
    new_state = schema.CartState.COMPLETE if not abort else schema.CartState.ABORTED
    with engine.begin() as connection:
        cart_row = query.fetchone(connection, schema.cart, cart, lock_for_update=True)
        if cart_row.state != schema.CartState.ACTIVE:
            raise ValueError("Cannot close an inactive cart.")

        query.update_cart(connection, id=cart, state=new_state)
        if not abort:
            query.decrement_cart_product_availability(connection, cart)

        cart_info = query.cart_info(connection, [cart])[0]
        return {'cart': cart_info}

if __name__ == '__main__':
    cli()
