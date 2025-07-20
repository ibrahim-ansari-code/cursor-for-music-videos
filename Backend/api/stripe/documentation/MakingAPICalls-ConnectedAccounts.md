---
title: Making API calls for connected accounts
subtitle: >-
  Learn how to add the right information to your API calls so you can make calls
  for your connected accounts.
route: /connect/authentication

---

# Making API calls for connected accounts

Learn how to add the right information to your API calls so you can make calls for your connected accounts.

You can make API calls for your connected accounts:

- Server-side with the [Stripe-Account header](#stripe-account-header) and the connected account ID, per request
- Client-side by passing the connected account ID as an argument to the client library

To help with performance and reliability, Stripe has established [rate limits and allocations](https://stripe.com/rate-limits) for API endpoints.

## Adding the Stripe-Account header server-side 

To make server-side API calls for connected accounts, use the `Stripe-Account` header with the account identifier, which begins with the prefix `acct_`. Here are four examples using your platform’s [API secret key](https://stripe.com/keys) and the connected account’s [Account](https://stripe.com/api/accounts) identifier:

#### Create PaymentIntent
Code snippet calling post /v1/payment_intents in curl (resource-based pattern).
```curl
curl https://api.stripe.com/v1/payment_intents \
  -u "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4:" \
  -H "Stripe-Account: {{CONNECTEDACCOUNT_ID}}" \
  -d amount=1000 \
  -d currency=usd
```
Code snippet calling post /v1/payment_intents in cli (resource-based pattern).
```cli
stripe payment_intents create  \
  --stripe-account {{CONNECTEDACCOUNT_ID}} \
  --amount=1000 \
  --currency=usd
```
Code snippet calling post /v1/payment_intents in ruby (resource-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
Stripe.api_key = 'sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4'

payment_intent = Stripe::PaymentIntent.create(
  {
    amount: 1000,
    currency: 'usd',
  },
  {stripe_account: '{{CONNECTEDACCOUNT_ID}}'},
)
```
Code snippet calling post /v1/payment_intents in ruby (service-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = Stripe::StripeClient.new("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

payment_intent = client.v1.payment_intents.create(
  {
    amount: 1000,
    currency: 'usd',
  },
  {stripe_account: '{{CONNECTEDACCOUNT_ID}}'},
)
```
Code snippet calling post /v1/payment_intents in python (resource-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
import stripe
stripe.api_key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

payment_intent = stripe.PaymentIntent.create(
  amount=1000,
  currency="usd",
  stripe_account="{{CONNECTEDACCOUNT_ID}}",
)
```
Code snippet calling post /v1/payment_intents in python (service-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

payment_intent = client.payment_intents.create(
  {"amount": 1000, "currency": "usd"},
  {"stripe_account": "{{CONNECTEDACCOUNT_ID}}"},
)
```
Code snippet calling post /v1/payment_intents in php (resource-based pattern).
```php
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
$stripe = new \Stripe\StripeClient('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

$paymentIntent = $stripe->paymentIntents->create(
  [
    'amount' => 1000,
    'currency' => 'usd',
  ],
  ['stripe_account' => '{{CONNECTEDACCOUNT_ID}}']
);
```
Code snippet calling post /v1/payment_intents in java (resource-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
Stripe.apiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

PaymentIntentCreateParams params =
  PaymentIntentCreateParams.builder().setAmount(1000L).setCurrency("usd").build();

RequestOptions requestOptions =
  RequestOptions.builder().setStripeAccount("{{CONNECTEDACCOUNT_ID}}").build();

PaymentIntent paymentIntent = PaymentIntent.create(params, requestOptions);
```
Code snippet calling post /v1/payment_intents in java (service-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeClient client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");

PaymentIntentCreateParams params =
  PaymentIntentCreateParams.builder().setAmount(1000L).setCurrency("usd").build();

RequestOptions requestOptions =
  RequestOptions.builder().setStripeAccount("{{CONNECTEDACCOUNT_ID}}").build();

PaymentIntent paymentIntent = client.paymentIntents().create(params, requestOptions);
```
Code snippet calling post /v1/payment_intents in node (resource-based pattern).
```node
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
const stripe = require('stripe')('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

const paymentIntent = await stripe.paymentIntents.create(
  {
    amount: 1000,
    currency: 'usd',
  },
  {
    stripeAccount: '{{CONNECTEDACCOUNT_ID}}',
  }
);
```
Code snippet calling post /v1/payment_intents in go (resource-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
stripe.Key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

params := &stripe.PaymentIntentParams{
  Amount: stripe.Int64(1000),
  Currency: stripe.String(stripe.CurrencyUSD),
};
params.SetStripeAccount("{{CONNECTEDACCOUNT_ID}}")
result, err := paymentintent.New(params);
```
Code snippet calling post /v1/payment_intents in go (service-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys

sc := stripe.NewClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
params := &stripe.PaymentIntentCreateParams{
  Amount: stripe.Int64(1000),
  Currency: stripe.String(stripe.CurrencyUSD),
};
params.SetStripeAccount("{{CONNECTEDACCOUNT_ID}}")
result, err := sc.V1PaymentIntents.Create(context.TODO(), params);
```
Code snippet calling post /v1/payment_intents in dotnet (resource-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeConfiguration.ApiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

var options = new PaymentIntentCreateOptions { Amount = 1000, Currency = "usd" };
var requestOptions = new RequestOptions
{
    StripeAccount = "{{CONNECTEDACCOUNT_ID}}",
};
var service = new PaymentIntentService();
PaymentIntent paymentIntent = service.Create(options, requestOptions);
```
Code snippet calling post /v1/payment_intents in dotnet (service-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
var options = new PaymentIntentCreateOptions { Amount = 1000, Currency = "usd" };
var requestOptions = new RequestOptions
{
    StripeAccount = "{{CONNECTEDACCOUNT_ID}}",
};
var client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
var service = client.V1.PaymentIntents;
PaymentIntent paymentIntent = service.Create(options, requestOptions);
```

#### Retrieve Balance
Code snippet calling get /v1/balance in curl (resource-based pattern).
```curl
curl https://api.stripe.com/v1/balance \
  -u "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4:" \
  -H "Stripe-Account: {{CONNECTEDACCOUNT_ID}}"
```
Code snippet calling get /v1/balance in cli (resource-based pattern).
```cli
stripe balance retrieve  \
  --stripe-account {{CONNECTEDACCOUNT_ID}}
```
Code snippet calling get /v1/balance in ruby (resource-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
Stripe.api_key = 'sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4'

balance = Stripe::Balance.retrieve({}, {stripe_account: '{{CONNECTEDACCOUNT_ID}}'})
```
Code snippet calling get /v1/balance in ruby (service-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = Stripe::StripeClient.new("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

balance = client.v1.balance.retrieve(
  {},
  {stripe_account: '{{CONNECTEDACCOUNT_ID}}'},
)
```
Code snippet calling get /v1/balance in python (resource-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
import stripe
stripe.api_key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

balance = stripe.Balance.retrieve(stripe_account="{{CONNECTEDACCOUNT_ID}}")
```
Code snippet calling get /v1/balance in python (service-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

balance = client.balance.retrieve(
  options={"stripe_account": "{{CONNECTEDACCOUNT_ID}}"},
)
```
Code snippet calling get /v1/balance in php (resource-based pattern).
```php
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
$stripe = new \Stripe\StripeClient('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

$balance = $stripe->balance->retrieve(
  [],
  ['stripe_account' => '{{CONNECTEDACCOUNT_ID}}']
);
```
Code snippet calling get /v1/balance in java (resource-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
Stripe.apiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

RequestOptions requestOptions =
  RequestOptions.builder().setStripeAccount("{{CONNECTEDACCOUNT_ID}}").build();

Balance balance = Balance.retrieve(requestOptions);
```
Code snippet calling get /v1/balance in java (service-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeClient client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");

BalanceRetrieveParams params = BalanceRetrieveParams.builder().build();

RequestOptions requestOptions =
  RequestOptions.builder().setStripeAccount("{{CONNECTEDACCOUNT_ID}}").build();

Balance balance = client.balance().retrieve(params, requestOptions);
```
Code snippet calling get /v1/balance in node (resource-based pattern).
```node
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
const stripe = require('stripe')('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

const balance = await stripe.balance.retrieve({
  stripeAccount: '{{CONNECTEDACCOUNT_ID}}',
});
```
Code snippet calling get /v1/balance in go (resource-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
stripe.Key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

params := &stripe.BalanceParams{};
params.SetStripeAccount("{{CONNECTEDACCOUNT_ID}}")
result, err := balance.Get(params);
```
Code snippet calling get /v1/balance in go (service-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys

sc := stripe.NewClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
params := &stripe.BalanceRetrieveParams{};
params.SetStripeAccount("{{CONNECTEDACCOUNT_ID}}")
result, err := sc.V1Balance.Retrieve(context.TODO(), params);
```
Code snippet calling get /v1/balance in dotnet (resource-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeConfiguration.ApiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

var options = new BalanceGetOptions();
var requestOptions = new RequestOptions
{
    StripeAccount = "{{CONNECTEDACCOUNT_ID}}",
};
var service = new BalanceService();
Balance balance = service.Get(options, requestOptions);
```
Code snippet calling get /v1/balance in dotnet (service-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
var options = new BalanceGetOptions();
var requestOptions = new RequestOptions
{
    StripeAccount = "{{CONNECTEDACCOUNT_ID}}",
};
var client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
var service = client.V1.Balance;
Balance balance = service.Get(options, requestOptions);
```

#### List Products
Code snippet calling get /v1/products in curl (resource-based pattern).
```curl
curl -G https://api.stripe.com/v1/products \
  -u "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4:" \
  -H "Stripe-Account: {{CONNECTEDACCOUNT_ID}}" \
  -d limit=5
```
Code snippet calling get /v1/products in cli (resource-based pattern).
```cli
stripe products list  \
  --stripe-account {{CONNECTEDACCOUNT_ID}} \
  --limit=5
```
Code snippet calling get /v1/products in ruby (resource-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
Stripe.api_key = 'sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4'

products = Stripe::Product.list(
  {limit: 5},
  {stripe_account: '{{CONNECTEDACCOUNT_ID}}'},
)
```
Code snippet calling get /v1/products in ruby (service-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = Stripe::StripeClient.new("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

products = client.v1.products.list(
  {limit: 5},
  {stripe_account: '{{CONNECTEDACCOUNT_ID}}'},
)
```
Code snippet calling get /v1/products in python (resource-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
import stripe
stripe.api_key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

products = stripe.Product.list(
  limit=5,
  stripe_account="{{CONNECTEDACCOUNT_ID}}",
)
```
Code snippet calling get /v1/products in python (service-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

products = client.products.list(
  {"limit": 5},
  {"stripe_account": "{{CONNECTEDACCOUNT_ID}}"},
)
```
Code snippet calling get /v1/products in php (resource-based pattern).
```php
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
$stripe = new \Stripe\StripeClient('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

$products = $stripe->products->all(
  ['limit' => 5],
  ['stripe_account' => '{{CONNECTEDACCOUNT_ID}}']
);
```
Code snippet calling get /v1/products in java (resource-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
Stripe.apiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

ProductListParams params = ProductListParams.builder().setLimit(5L).build();

RequestOptions requestOptions =
  RequestOptions.builder().setStripeAccount("{{CONNECTEDACCOUNT_ID}}").build();

ProductCollection products = Product.list(params, requestOptions);
```
Code snippet calling get /v1/products in java (service-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeClient client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");

ProductListParams params = ProductListParams.builder().setLimit(5L).build();

RequestOptions requestOptions =
  RequestOptions.builder().setStripeAccount("{{CONNECTEDACCOUNT_ID}}").build();

StripeCollection<Product> stripeCollection =
  client.products().list(params, requestOptions);
```
Code snippet calling get /v1/products in node (resource-based pattern).
```node
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
const stripe = require('stripe')('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

const products = await stripe.products.list(
  {
    limit: 5,
  },
  {
    stripeAccount: '{{CONNECTEDACCOUNT_ID}}',
  }
);
```
Code snippet calling get /v1/products in go (resource-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
stripe.Key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

params := &stripe.ProductListParams{};
params.Limit = stripe.Int64(5)
params.SetStripeAccount("{{CONNECTEDACCOUNT_ID}}")
result := product.List(params);
```
Code snippet calling get /v1/products in go (service-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys

sc := stripe.NewClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
params := &stripe.ProductListParams{};
params.Limit = stripe.Int64(5)
params.SetStripeAccount("{{CONNECTEDACCOUNT_ID}}")
result := sc.V1Products.List(context.TODO(), params);
```
Code snippet calling get /v1/products in dotnet (resource-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeConfiguration.ApiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

var options = new ProductListOptions { Limit = 5 };
var requestOptions = new RequestOptions
{
    StripeAccount = "{{CONNECTEDACCOUNT_ID}}",
};
var service = new ProductService();
StripeList<Product> products = service.List(options, requestOptions);
```
Code snippet calling get /v1/products in dotnet (service-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
var options = new ProductListOptions { Limit = 5 };
var requestOptions = new RequestOptions
{
    StripeAccount = "{{CONNECTEDACCOUNT_ID}}",
};
var client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
var service = client.V1.Products;
StripeList<Product> products = service.List(options, requestOptions);
```

#### Delete Customer
Code snippet calling delete /v1/customers/{customer} in curl (resource-based pattern).
```curl
curl -X DELETE https://api.stripe.com/v1/customers/{{CUSTOMER_ID}} \
  -u "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4:" \
  -H "Stripe-Account: {{CONNECTEDACCOUNT_ID}}"
```
Code snippet calling delete /v1/customers/{customer} in cli (resource-based pattern).
```cli
stripe customers delete {{CUSTOMER_ID}} \
  --stripe-account {{CONNECTEDACCOUNT_ID}}
```
Code snippet calling delete /v1/customers/{customer} in ruby (resource-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
Stripe.api_key = 'sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4'

deleted = Stripe::Customer.delete(
  '{{CUSTOMER_ID}}',
  {},
  {stripe_account: '{{CONNECTEDACCOUNT_ID}}'},
)
```
Code snippet calling delete /v1/customers/{customer} in ruby (service-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = Stripe::StripeClient.new("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

deleted = client.v1.customers.delete(
  '{{CUSTOMER_ID}}',
  {},
  {stripe_account: '{{CONNECTEDACCOUNT_ID}}'},
)
```
Code snippet calling delete /v1/customers/{customer} in python (resource-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
import stripe
stripe.api_key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

deleted = stripe.Customer.delete(
  "{{CUSTOMER_ID}}",
  stripe_account="{{CONNECTEDACCOUNT_ID}}",
)
```
Code snippet calling delete /v1/customers/{customer} in python (service-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

deleted = client.customers.delete(
  "{{CUSTOMER_ID}}",
  options={"stripe_account": "{{CONNECTEDACCOUNT_ID}}"},
)
```
Code snippet calling delete /v1/customers/{customer} in php (resource-based pattern).
```php
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
$stripe = new \Stripe\StripeClient('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

$deleted = $stripe->customers->delete(
  '{{CUSTOMER_ID}}',
  [],
  ['stripe_account' => '{{CONNECTEDACCOUNT_ID}}']
);
```
Code snippet calling delete /v1/customers/{customer} in java (resource-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
Stripe.apiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

Customer resource = Customer.retrieve("{{CUSTOMER_ID}}");

RequestOptions requestOptions =
  RequestOptions.builder().setStripeAccount("{{CONNECTEDACCOUNT_ID}}").build();

Customer customer = resource.delete(requestOptions);
```
Code snippet calling delete /v1/customers/{customer} in java (service-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeClient client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");

RequestOptions requestOptions =
  RequestOptions.builder().setStripeAccount("{{CONNECTEDACCOUNT_ID}}").build();

Customer customer = client.customers().delete("{{CUSTOMER_ID}}", requestOptions);
```
Code snippet calling delete /v1/customers/{customer} in node (resource-based pattern).
```node
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
const stripe = require('stripe')('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

const deleted = await stripe.customers.del(
  '{{CUSTOMER_ID}}',
  {
    stripeAccount: '{{CONNECTEDACCOUNT_ID}}',
  }
);
```
Code snippet calling delete /v1/customers/{customer} in go (resource-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
stripe.Key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

params := &stripe.CustomerParams{};
params.SetStripeAccount("{{CONNECTEDACCOUNT_ID}}")
result, err := customer.Del("{{CUSTOMER_ID}}", params);
```
Code snippet calling delete /v1/customers/{customer} in go (service-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys

sc := stripe.NewClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
params := &stripe.CustomerDeleteParams{Customer: stripe.String("{{CUSTOMER_ID}}")};
params.SetStripeAccount("{{CONNECTEDACCOUNT_ID}}")
result, err := sc.V1Customers.Delete(context.TODO(), params);
```
Code snippet calling delete /v1/customers/{customer} in dotnet (resource-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeConfiguration.ApiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

var requestOptions = new RequestOptions
{
    StripeAccount = "{{CONNECTEDACCOUNT_ID}}",
};
var service = new CustomerService();
Customer deleted = service.Delete("{{CUSTOMER_ID}}", null, requestOptions);
```
Code snippet calling delete /v1/customers/{customer} in dotnet (service-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
var requestOptions = new RequestOptions
{
    StripeAccount = "{{CONNECTEDACCOUNT_ID}}",
};
var client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
var service = client.V1.Customers;
Customer deleted = service.Delete("{{CUSTOMER_ID}}", null, requestOptions);
```

The `Stripe-Account` header approach is implied in any API request that includes the Stripe account ID in the URL. Here’s an example that shows how to [Retrieve an account](https://stripe.com/api/accounts/retrieve) with your user’s [Account](https://stripe.com/api/accounts) identifier in the URL.
Code snippet calling get /v1/accounts/{account} in curl (resource-based pattern).
```curl
curl https://api.stripe.com/v1/accounts/{{CONNECTEDACCOUNT_ID}} \
  -u "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4:"
```
Code snippet calling get /v1/accounts/{account} in cli (resource-based pattern).
```cli
stripe accounts retrieve {{CONNECTEDACCOUNT_ID}}
```
Code snippet calling get /v1/accounts/{account} in ruby (resource-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
Stripe.api_key = 'sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4'

account = Stripe::Account.retrieve('{{CONNECTEDACCOUNT_ID}}')
```
Code snippet calling get /v1/accounts/{account} in ruby (service-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = Stripe::StripeClient.new("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

account = client.v1.accounts.retrieve('{{CONNECTEDACCOUNT_ID}}')
```
Code snippet calling get /v1/accounts/{account} in python (resource-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
import stripe
stripe.api_key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

account = stripe.Account.retrieve("{{CONNECTEDACCOUNT_ID}}")
```
Code snippet calling get /v1/accounts/{account} in python (service-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

account = client.accounts.retrieve("{{CONNECTEDACCOUNT_ID}}")
```
Code snippet calling get /v1/accounts/{account} in php (resource-based pattern).
```php
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
$stripe = new \Stripe\StripeClient('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

$account = $stripe->accounts->retrieve('{{CONNECTEDACCOUNT_ID}}', []);
```
Code snippet calling get /v1/accounts/{account} in java (resource-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
Stripe.apiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

Account account = Account.retrieve("{{CONNECTEDACCOUNT_ID}}");
```
Code snippet calling get /v1/accounts/{account} in java (service-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeClient client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");

AccountRetrieveParams params = AccountRetrieveParams.builder().build();

Account account = client.accounts().retrieve("{{CONNECTEDACCOUNT_ID}}", params);
```
Code snippet calling get /v1/accounts/{account} in node (resource-based pattern).
```node
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
const stripe = require('stripe')('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

const account = await stripe.accounts.retrieve('{{CONNECTEDACCOUNT_ID}}');
```
Code snippet calling get /v1/accounts/{account} in go (resource-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
stripe.Key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

params := &stripe.AccountParams{};
result, err := account.GetByID("{{CONNECTEDACCOUNT_ID}}", params);
```
Code snippet calling get /v1/accounts/{account} in go (service-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys

sc := stripe.NewClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
params := &stripe.AccountRetrieveParams{
  Account: stripe.String("{{CONNECTEDACCOUNT_ID}}"),
};
result, err := sc.V1Accounts.GetByID(context.TODO(), params);
```
Code snippet calling get /v1/accounts/{account} in dotnet (resource-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeConfiguration.ApiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

var service = new AccountService();
Account account = service.Get("{{CONNECTEDACCOUNT_ID}}");
```
Code snippet calling get /v1/accounts/{account} in dotnet (service-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
var client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
var service = client.V1.Accounts;
Account account = service.Get("{{CONNECTEDACCOUNT_ID}}");
```

All of Stripe’s server-side libraries support this approach on a per-request basis:
Code snippet calling post /v1/customers in curl (resource-based pattern).
```curl
curl https://api.stripe.com/v1/customers \
  -u "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4:" \
  -H "Stripe-Account: {{CONNECTEDACCOUNT_ID}}" \
  --data-urlencode email="person@example.com"
```
Code snippet calling post /v1/customers in cli (resource-based pattern).
```cli
stripe customers create  \
  --stripe-account {{CONNECTEDACCOUNT_ID}} \
  --email="person@example.com"
```
Code snippet calling post /v1/customers in ruby (resource-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
Stripe.api_key = 'sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4'

customer = Stripe::Customer.create(
  {email: 'person@example.com'},
  {stripe_account: '{{CONNECTEDACCOUNT_ID}}'},
)
```
Code snippet calling post /v1/customers in ruby (service-based pattern).
```ruby
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = Stripe::StripeClient.new("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

customer = client.v1.customers.create(
  {email: 'person@example.com'},
  {stripe_account: '{{CONNECTEDACCOUNT_ID}}'},
)
```
Code snippet calling post /v1/customers in python (resource-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
import stripe
stripe.api_key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

customer = stripe.Customer.create(
  email="person@example.com",
  stripe_account="{{CONNECTEDACCOUNT_ID}}",
)
```
Code snippet calling post /v1/customers in python (service-based pattern).
```python
# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
client = StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4")

customer = client.customers.create(
  {"email": "person@example.com"},
  {"stripe_account": "{{CONNECTEDACCOUNT_ID}}"},
)
```
Code snippet calling post /v1/customers in php (resource-based pattern).
```php
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
$stripe = new \Stripe\StripeClient('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

$customer = $stripe->customers->create(
  ['email' => 'person@example.com'],
  ['stripe_account' => '{{CONNECTEDACCOUNT_ID}}']
);
```
Code snippet calling post /v1/customers in java (resource-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
Stripe.apiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

CustomerCreateParams params =
  CustomerCreateParams.builder().setEmail("person@example.com").build();

RequestOptions requestOptions =
  RequestOptions.builder().setStripeAccount("{{CONNECTEDACCOUNT_ID}}").build();

Customer customer = Customer.create(params, requestOptions);
```
Code snippet calling post /v1/customers in java (service-based pattern).
```java
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeClient client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");

CustomerCreateParams params =
  CustomerCreateParams.builder().setEmail("person@example.com").build();

RequestOptions requestOptions =
  RequestOptions.builder().setStripeAccount("{{CONNECTEDACCOUNT_ID}}").build();

Customer customer = client.customers().create(params, requestOptions);
```
Code snippet calling post /v1/customers in node (resource-based pattern).
```node
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
const stripe = require('stripe')('sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4');

const customer = await stripe.customers.create(
  {
    email: 'person@example.com',
  },
  {
    stripeAccount: '{{CONNECTEDACCOUNT_ID}}',
  }
);
```
Code snippet calling post /v1/customers in go (resource-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
stripe.Key = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4"

params := &stripe.CustomerParams{Email: stripe.String("person@example.com")};
params.SetStripeAccount("{{CONNECTEDACCOUNT_ID}}")
result, err := customer.New(params);
```
Code snippet calling post /v1/customers in go (service-based pattern).
```go
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys

sc := stripe.NewClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
params := &stripe.CustomerCreateParams{Email: stripe.String("person@example.com")};
params.SetStripeAccount("{{CONNECTEDACCOUNT_ID}}")
result, err := sc.V1Customers.Create(context.TODO(), params);
```
Code snippet calling post /v1/customers in dotnet (resource-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
StripeConfiguration.ApiKey = "sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4";

var options = new CustomerCreateOptions { Email = "person@example.com" };
var requestOptions = new RequestOptions
{
    StripeAccount = "{{CONNECTEDACCOUNT_ID}}",
};
var service = new CustomerService();
Customer customer = service.Create(options, requestOptions);
```
Code snippet calling post /v1/customers in dotnet (service-based pattern).
```dotnet
// Set your secret key. Remember to switch to your live secret key in production.
// See your keys here: https://dashboard.stripe.com/apikeys
var options = new CustomerCreateOptions { Email = "person@example.com" };
var requestOptions = new RequestOptions
{
    StripeAccount = "{{CONNECTEDACCOUNT_ID}}",
};
var client = new StripeClient("sk_test_51RDsHmKoVREUyxXNFoZgNdL353ATEepV68bnHjti42ts2gLs5Fh0WhOKQcdNFgdgtvKlJZzAVDyCxL3Ka329XubI00KR77ecX4");
var service = client.V1.Customers;
Customer customer = service.Create(options, requestOptions);
```

## Adding the connected account ID to a client-side application

Client-side libraries set the connected account ID as an argument to the client application:

#### HTML + JS

The JavaScript code for passing the connected account ID client-side is the same for plain JS and for ESNext.

```javascript
var stripe = Stripe('pk_test_51RDsHmKoVREUyxXNpqZgiWKLEPqfgLlG41YTFIxZokdXCtSVkL8COEnO5h9clvAg2LZsDg2WNQG11MYsSHho9PKd00aUgr7JVc', {
  stripeAccount: '{{CONNECTED_ACCOUNT_ID}}',
});
```

#### React

```javascript
import {loadStripe} from '@stripe/stripe-js';

// Make sure to call `loadStripe` outside of a component's render to avoid
// recreating the `Stripe` object on every render.
const stripePromise = loadStripe('pk_test_51RDsHmKoVREUyxXNpqZgiWKLEPqfgLlG41YTFIxZokdXCtSVkL8COEnO5h9clvAg2LZsDg2WNQG11MYsSHho9PKd00aUgr7JVc', {
  stripeAccount: '{{CONNECTED_ACCOUNT_ID}}',
});
```

#### iOS

#### Android

#### React Native

```javascript
import {StripeProvider} from '@stripe/stripe-react-native';

function App() {
  return (
    <StripeProvider
      publishableKey="pk_test_51RDsHmKoVREUyxXNpqZgiWKLEPqfgLlG41YTFIxZokdXCtSVkL8COEnO5h9clvAg2LZsDg2WNQG11MYsSHho9PKd00aUgr7JVc"
      stripeAccountId="{{CONNECTED_ACCOUNT_ID}}"
    >
      // Your app code here
    </StripeProvider>
  );
}
```