# Từ điển trường dữ liệu

Sinh từ Django models; kiểu DB trên MySQL thực đang chạy. PK bigint tự tăng, FK tham chiếu theo cột target, mọi constraint do migration quản lý.

## auth.Permission — `auth_permission`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | integer AUTO_INCREMENT | False | PK |
| name | varchar(255) | False |  |
| content_type | integer | False | FK contenttypes.ContentType |
| codename | varchar(100) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## auth.Group_permissions — `auth_group_permissions`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | integer AUTO_INCREMENT | False | PK |
| group | integer | False | FK auth.Group |
| permission | integer | False | FK auth.Permission |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## auth.Group — `auth_group`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | integer AUTO_INCREMENT | False | PK |
| name | varchar(150) | False | UNIQUE |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## contenttypes.ContentType — `django_content_type`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | integer AUTO_INCREMENT | False | PK |
| app_label | varchar(100) | False |  |
| model | varchar(100) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## sessions.Session — `django_session`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| session_key | varchar(40) | False | PK |
| session_data | longtext | False |  |
| expire_date | datetime(6) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## common.AuditLog — `common_auditlog`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| actor | bigint | True | FK accounts.User |
| store | bigint | True | FK stores.Store |
| action | varchar(80) | False |  |
| object_type | varchar(80) | False |  |
| object_id | varchar(80) | False |  |
| changes | json | False |  |
| created_at | datetime(6) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## common.IdempotencyRecord — `common_idempotencyrecord`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| scope | varchar(100) | False |  |
| key | varchar(100) | False |  |
| fingerprint | varchar(64) | False |  |
| order | bigint | True | FK orders.Order |
| created_at | datetime(6) | False |  |

Constraints: <UniqueConstraint: fields=('scope', 'key') name='idempotency_scope_key'>

Indexes: PK/unique/FK indexes mặc định.

## accounts.User_groups — `accounts_user_groups`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| user | bigint | False | FK accounts.User |
| group | integer | False | FK auth.Group |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## accounts.User_user_permissions — `accounts_user_user_permissions`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| user | bigint | False | FK accounts.User |
| permission | integer | False | FK auth.Permission |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## accounts.User — `accounts_user`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| password | varchar(128) | False |  |
| last_login | datetime(6) | True |  |
| is_superuser | bool | False |  |
| first_name | varchar(150) | False |  |
| last_name | varchar(150) | False |  |
| is_staff | bool | False |  |
| is_active | bool | False |  |
| date_joined | datetime(6) | False |  |
| email | varchar(254) | False | UNIQUE |
| full_name | varchar(150) | False |  |

Constraints: <UniqueConstraint: expressions=(Lower(F(email)),) name='user_email_lower_unique'>

Indexes: PK/unique/FK indexes mặc định.

## accounts.Employee — `accounts_employee`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| user | bigint | False | FK accounts.User |
| code | varchar(50) | False | UNIQUE |
| phone | varchar(30) | False |  |
| title | varchar(150) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## accounts.RoleAssignment — `accounts_roleassignment`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| user | bigint | False | FK accounts.User |
| group | integer | False | FK auth.Group |
| store | bigint | False | FK stores.Store |

Constraints: <UniqueConstraint: fields=('user', 'group', 'store') name='unique_branch_role'>

Indexes: PK/unique/FK indexes mặc định.

## accounts.SocialIdentity — `accounts_socialidentity`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| user | bigint | False | FK accounts.User |
| provider | varchar(20) | False |  |
| subject | varchar(255) | False |  |

Constraints: <UniqueConstraint: fields=('provider', 'subject') name='social_provider_subject'>

Indexes: PK/unique/FK indexes mặc định.

## accounts.ResetChallenge — `accounts_resetchallenge`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| user | bigint | False | FK accounts.User |
| token_hash | varchar(64) | False | UNIQUE |
| expires_at | datetime(6) | False |  |
| used_at | datetime(6) | True |  |
| created_at | datetime(6) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## products.Category — `products_category`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| name | varchar(150) | False | UNIQUE |
| source_key | varchar(100) | False | UNIQUE |
| is_active | bool | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## products.Brand — `products_brand`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| name | varchar(150) | False | UNIQUE |
| is_active | bool | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## products.Product — `products_product`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| name | varchar(500) | False |  |
| slug | varchar(250) | False | UNIQUE |
| category | bigint | False | FK products.Category |
| brand | bigint | False | FK products.Brand |
| description | longtext | False |  |
| raw_specs | longtext | False |  |
| source_namespace | varchar(60) | False |  |
| source_id | varchar(80) | False |  |
| original_slug | varchar(500) | False |  |
| source_url | varchar(1000) | False |  |
| source_snapshot | json | False |  |
| is_active | bool | False |  |

Constraints: <UniqueConstraint: fields=('source_namespace', 'source_id') name='product_source_identity'>

Indexes: PK/unique/FK indexes mặc định.

## products.ProductVariant — `products_productvariant`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| product | bigint | False | FK products.Product |
| sku | varchar(100) | False | UNIQUE |
| name | varchar(200) | False |  |
| price | numeric(18, 2) | False |  |
| condition | varchar(100) | False |  |
| warranty_months | integer UNSIGNED | False |  |
| attributes | json | False |  |
| is_active | bool | False |  |

Constraints: <CheckConstraint: condition=(AND: ('price__gte', 0)) name='variant_price_nonnegative'>

Indexes: PK/unique/FK indexes mặc định.

## products.ProductImage — `products_productimage`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| product | bigint | False | FK products.Product |
| url | varchar(1500) | False |  |
| display_order | integer UNSIGNED | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## products.SpecificationDefinition — `products_specificationdefinition`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| name | varchar(200) | False | UNIQUE |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## products.ProductSpecification — `products_productspecification`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| product | bigint | False | FK products.Product |
| definition | bigint | False | FK products.SpecificationDefinition |
| value | longtext | False |  |
| numeric_value | numeric(18, 4) | True |  |
| unit | varchar(30) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: <Index: fields=['definition', 'numeric_value'] name='products_pr_definit_762f77_idx'>

## stores.Store — `stores_store`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| name | varchar(200) | False | UNIQUE |
| address | varchar(500) | False |  |
| phone | varchar(30) | False |  |
| is_active | bool | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## stores.Warehouse — `stores_warehouse`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| store | bigint | False | FK stores.Store |
| name | varchar(200) | False |  |
| is_active | bool | False |  |

Constraints: <UniqueConstraint: fields=('store', 'name') name='warehouse_store_name'>

Indexes: PK/unique/FK indexes mặc định.

## inventory.InventoryBalance — `inventory_inventorybalance`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| warehouse | bigint | False | FK stores.Warehouse |
| variant | bigint | False | FK products.ProductVariant |
| on_hand | integer UNSIGNED | False |  |
| reserved | integer UNSIGNED | False |  |
| alert_threshold | integer UNSIGNED | False |  |

Constraints: <UniqueConstraint: fields=('warehouse', 'variant') name='balance_warehouse_variant'>; <CheckConstraint: condition=(AND: ('on_hand__gte', F(reserved))) name='balance_reserved_lte_onhand'>

Indexes: PK/unique/FK indexes mặc định.

## inventory.StockDocument — `inventory_stockdocument`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| warehouse | bigint | False | FK stores.Warehouse |
| supplier | bigint | True | FK suppliers.Supplier |
| kind | varchar(10) | False |  |
| status | varchar(15) | False |  |
| reason | varchar(500) | False |  |
| created_by | bigint | False | FK accounts.User |
| posted_by | bigint | True | FK accounts.User |
| posted_at | datetime(6) | True |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## inventory.StockDocumentItem — `inventory_stockdocumentitem`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| document | bigint | False | FK inventory.StockDocument |
| variant | bigint | False | FK products.ProductVariant |
| quantity | integer | False |  |

Constraints: <UniqueConstraint: fields=('document', 'variant') name='document_variant'>; <CheckConstraint: condition=(NOT (AND: ('quantity', 0))) name='document_nonzero_quantity'>

Indexes: PK/unique/FK indexes mặc định.

## inventory.StockTransfer — `inventory_stocktransfer`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| source | bigint | False | FK stores.Warehouse |
| destination | bigint | False | FK stores.Warehouse |
| status | varchar(15) | False |  |
| reason | varchar(500) | False |  |
| created_by | bigint | False | FK accounts.User |
| approved_at | datetime(6) | True |  |
| dispatched_at | datetime(6) | True |  |
| received_at | datetime(6) | True |  |

Constraints: <CheckConstraint: condition=(NOT (AND: ('source', F(destination)))) name='transfer_different_warehouses'>

Indexes: PK/unique/FK indexes mặc định.

## inventory.StockTransferItem — `inventory_stocktransferitem`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| transfer | bigint | False | FK inventory.StockTransfer |
| variant | bigint | False | FK products.ProductVariant |
| quantity | integer UNSIGNED | False |  |

Constraints: <UniqueConstraint: fields=('transfer', 'variant') name='transfer_variant'>; <CheckConstraint: condition=(AND: ('quantity__gt', 0)) name='transfer_positive_quantity'>

Indexes: PK/unique/FK indexes mặc định.

## inventory.InventoryReservation — `inventory_inventoryreservation`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| balance | bigint | False | FK inventory.InventoryBalance |
| order | bigint | True | FK orders.Order |
| transfer | bigint | True | FK inventory.StockTransfer |
| quantity | integer UNSIGNED | False |  |
| status | varchar(15) | False |  |
| expires_at | datetime(6) | True |  |

Constraints: <CheckConstraint: condition=(OR: (AND: ('order__isnull', False), ('transfer__isnull', True)), (AND: ('order__isnull', True), ('transfer__isnull', False))) name='reservation_exactly_one_source'>; <CheckConstraint: condition=(AND: ('quantity__gt', 0)) name='reservation_quantity_positive'>

Indexes: <Index: fields=['status', 'expires_at'] name='inventory_i_status_6d8892_idx'>

## inventory.ReservationHistory — `inventory_reservationhistory`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| reservation | bigint | False | FK inventory.InventoryReservation |
| status | varchar(15) | False |  |
| created_at | datetime(6) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## inventory.StockMovement — `inventory_stockmovement`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| balance | bigint | False | FK inventory.InventoryBalance |
| delta | integer | False |  |
| on_hand_after | integer UNSIGNED | False |  |
| kind | varchar(30) | False |  |
| reference | varchar(100) | False |  |
| actor | bigint | True | FK accounts.User |
| created_at | datetime(6) | False |  |

Constraints: <UniqueConstraint: fields=('balance', 'kind', 'reference') name='movement_unique_source'>

Indexes: <Index: fields=['balance', 'created_at'] name='inventory_s_balance_cb675c_idx'>

## customers.Customer — `customers_customer`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| user | bigint | True | FK accounts.User |
| name | varchar(150) | False |  |
| phone | varchar(30) | False |  |
| email | varchar(254) | False |  |
| address | varchar(500) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## orders.Cart — `orders_cart`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| user | bigint | False | FK accounts.User |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## orders.CartItem — `orders_cartitem`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| cart | bigint | False | FK orders.Cart |
| variant | bigint | False | FK products.ProductVariant |
| quantity | integer UNSIGNED | False |  |

Constraints: <UniqueConstraint: fields=('cart', 'variant') name='cart_variant'>; <CheckConstraint: condition=(AND: ('quantity__gt', 0)) name='cart_positive_quantity'>

Indexes: PK/unique/FK indexes mặc định.

## orders.Order — `orders_order`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| created_at | datetime(6) | False |  |
| updated_at | datetime(6) | False |  |
| code | varchar(30) | False | UNIQUE |
| customer | bigint | False | FK customers.Customer |
| warehouse | bigint | False | FK stores.Warehouse |
| seller | bigint | True | FK accounts.User |
| channel | varchar(15) | False |  |
| status | varchar(15) | False |  |
| payment_method | varchar(20) | False |  |
| payment_status | varchar(20) | False |  |
| recipient_name | varchar(150) | False |  |
| phone | varchar(30) | False |  |
| address | varchar(500) | False |  |
| fulfillment | varchar(15) | False |  |
| subtotal | numeric(18, 2) | False |  |
| shipping_fee | numeric(18, 2) | False |  |
| grand_total | numeric(18, 2) | False |  |
| expires_at | datetime(6) | True |  |
| completed_at | datetime(6) | True |  |
| paid_at | datetime(6) | True |  |

Constraints: Django PK/FK/field unique.

Indexes: <Index: fields=['warehouse', 'status', 'created_at'] name='orders_orde_warehou_25bc40_idx'>

## orders.OrderItem — `orders_orderitem`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| order | bigint | False | FK orders.Order |
| variant | bigint | False | FK products.ProductVariant |
| name | varchar(500) | False |  |
| sku | varchar(100) | False |  |
| attributes | json | False |  |
| quantity | integer UNSIGNED | False |  |
| unit_price | numeric(18, 2) | False |  |
| discount | numeric(18, 2) | False |  |
| line_total | numeric(18, 2) | False |  |

Constraints: <CheckConstraint: condition=(AND: ('quantity__gt', 0)) name='order_quantity_positive'>

Indexes: PK/unique/FK indexes mặc định.

## orders.OrderStatusHistory — `orders_orderstatushistory`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| order | bigint | False | FK orders.Order |
| status | varchar(15) | False |  |
| reason | varchar(500) | False |  |
| actor | bigint | True | FK accounts.User |
| created_at | datetime(6) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## orders.Invoice — `orders_invoice`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| order | bigint | False | FK orders.Order |
| code | varchar(40) | False | UNIQUE |
| snapshot | json | False |  |
| created_at | datetime(6) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## orders.OTPChallenge — `orders_otpchallenge`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | char(32) | False | PK |
| order | bigint | False | FK orders.Order |
| code_hash | varchar(128) | False |  |
| attempts | integer UNSIGNED | False |  |
| expires_at | datetime(6) | False |  |
| used_at | datetime(6) | True |  |
| created_at | datetime(6) | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.

## payments.PaymentTransaction — `payments_paymenttransaction`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| order | bigint | False | FK orders.Order |
| kind | varchar(15) | False |  |
| amount | numeric(18, 2) | False |  |
| key | varchar(100) | False |  |
| reference | varchar(200) | False |  |
| actor | bigint | False | FK accounts.User |
| created_at | datetime(6) | False |  |

Constraints: <UniqueConstraint: fields=('order', 'key') name='payment_order_key'>; <CheckConstraint: condition=(AND: ('amount__gt', 0)) name='payment_amount_positive'>

Indexes: PK/unique/FK indexes mặc định.

## suppliers.Supplier — `suppliers_supplier`

| Field | MySQL type | Null | Key / reference |
|---|---|---|---|
| id | bigint AUTO_INCREMENT | False | PK |
| name | varchar(200) | False |  |
| phone | varchar(30) | False |  |
| email | varchar(254) | False |  |
| address | varchar(500) | False |  |
| is_active | bool | False |  |

Constraints: Django PK/FK/field unique.

Indexes: PK/unique/FK indexes mặc định.
