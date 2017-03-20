# Everlane take-home

This is a solution for https://gist.github.com/mtthgn/e2b4246f6d81da626715efc106ad0c79.

## Notes

User management system is eschewed, users will need to keep track of their cart numbers.

Also, currently products are assumed to be static - i.e. their price will not change over time.

## Building

For this app to run, you will need python 2.7 as well as a local postgresql database.

### Postgres
For postgres, either have it running on localhost:5432 or start it
by installing [docker-compose](https://docs.docker.com/compose/install/) and running

```
docker-compose up
```

### Python dependencies

To install python dependencies, run `pip install -r requirements.txt`

## Running

To run automated tests, invoke `py.test` which will test all the major CLI invocations.

Once dependencies are set up, you can run `cart.py`, which will show help text by default.

Note that you can invoke specific subcommands without the command line flags will automatically prompt for values.

Concrete actions you can do are outlined below:

### Setting up the database
```bash
$ ./cart.py setup
{
  "command": "setup",
  "dbUrl": "postgresql://localhost",
  "success": true
}
```

### Adding a new product

```bash
$ ./cart.py add_product --title foobar --price 3.4 --available_inventory 10
{
  "product": {
    "price": 3.40,
    "available_inventory": 10,
    "id": 1,
    "title": "foobar"
  },
  "command": "add_product",
  "success": true
}
```


### Creating a shopping cart
```bash
$ ./cart.py create_cart
{
  "command": "create_cart",
  "success": true,
  "cart": {
    "state": "active",
    "id": 1
  }
}
```

### Adding a product to a shopping cart

```bash
$ ./cart.py  update_cart --cart 1 --product 1 --amount 4
{
  "command": "update_cart",
  "success": true
}
```

Note that if a product already exists in cart, the amount is _changed_ to what is specified.

The amount passed has to be at most the products `available_inventory`.

### Removing a product from a shopping cart

Removing an item requires changing amount to 0.

```bash
$ ./cart.py  update_cart --cart 1 --product 1 --amount 0
{
  "command": "update_cart",
  "success": true
}
```

### Looking at the contents of cart(s)

This can be used to look at purchase history.

```bash
./cart.py show_cart --cart 1 --cart 2
{
  "carts": [
    {
      "state": "active",
      "total_price": 13.60,
      "products": [
        {
          "price": 3.40,
          "amount": 4,
          "product_id": 1,
          "title": "foobar"
        }
      ],
      "id": 1
    },
    {
      "state": "active",
      "total_price": 17.00,
      "products": [
        {
          "price": 3.40,
          "amount": 5,
          "product_id": 1,
          "title": "foobar"
        }
      ],
      "id": 2
    }
  ],
  "command": "show_cart",
  "success": true
}
```

State `active` means the customer has yet to purchase the items, other valid values are `complete` and `aborted`.

### Closing a cart

To finish a purchase, a user can close a cart which will:
- display the items purchased, total amount
- change cart state to `complete`
- reduce each products' available_inventory

Note that if some products being purchased don't have enough `available_inventory`, this operation will fail.

```bash
⟩ ./cart.py close_cart --cart 1
{
  "command": "close_cart",
  "success": true,
  "cart": {
    "state": "complete",
    "total_price": 13.60,
    "products": [
      {
        "price": 3.40,
        "amount": 4,
        "product_id": 1,
        "title": "foobar"
      }
    ],
    "id": 1
  }
}
```

### Aborting a cart

If a customer desires to abandon a cart, this can be done so:

```bash
$ ./cart.py close_cart --cart 2 --abort
{
  "command": "close_cart",
  "success": true,
  "cart": {
    "state": "aborted",
    "total_price": 17.00,
    "products": [
      {
        "price": 3.40,
        "amount": 5,
        "product_id": 1,
        "title": "foobar"
      }
    ],
    "id": 2
  }
}
```
