from sqlalchemy import Table, Column, DateTime, Enum, Integer, String, MetaData, Numeric, ForeignKey, UniqueConstraint, CheckConstraint

metadata = MetaData()

class CartState:
    ACTIVE = 1
    COMPLETE = 2
    ABORTED = 3

    @staticmethod
    def to_string(state):
        if state == CartState.ACTIVE: return 'active'
        if state == CartState.COMPLETE: return 'complete'
        if state == CartState.ABORTED: return 'aborted'
        raise ValueError("Unknown CartState: {}".format(state))

products = Table('products', metadata,
    Column('id', Integer, primary_key=True),
    Column('price', Numeric(8, 2), nullable=False),
    Column('title', String(255), nullable=False),
    Column('available_inventory', Integer, CheckConstraint('available_inventory>=0'), nullable=False)
)

cart = Table('cart', metadata,
    Column('id', Integer, primary_key=True),
    Column('state', Integer),
    # Column('started_at', DateTime, nullable=False),
    # Column('updated_at', DateTime, nullable=False)
)

cart_contents = Table('cart_contents', metadata,
    Column('cart_id', Integer, ForeignKey('cart.id'), nullable=False),
    Column('product_id', Integer, ForeignKey('products.id'), nullable=False),
    Column('amount', Integer, CheckConstraint('amount>=0'), nullable=False),
    UniqueConstraint('cart_id', 'product_id', name='c_cart_contents_uniq')
)
