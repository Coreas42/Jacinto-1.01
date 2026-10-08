"""
Validadores para el sistema de inventario y POS.
Proporciona funciones de validación reutilizables para garantizar integridad de datos.
"""


class ValidationError(Exception):
    """Excepción personalizada para errores de validación."""
    pass


class ProductValidator:
    """Valida datos de productos."""

    @staticmethod
    def validate_sku(sku: str) -> str:
        """Valida y limpia el SKU."""
        if not sku or not isinstance(sku, str):
            raise ValidationError("SKU no puede estar vacío.")
        sku = sku.strip().upper()
        if len(sku) < 2:
            raise ValidationError("SKU debe tener al menos 2 caracteres.")
        if len(sku) > 50:
            raise ValidationError("SKU no puede exceder 50 caracteres.")
        return sku

    @staticmethod
    def validate_name(name: str) -> str:
        """Valida y limpia el nombre del producto."""
        if not name or not isinstance(name, str):
            raise ValidationError("Nombre no puede estar vacío.")
        name = name.strip()
        if len(name) < 3:
            raise ValidationError("Nombre debe tener al menos 3 caracteres.")
        if len(name) > 150:
            raise ValidationError("Nombre no puede exceder 150 caracteres.")
        return name

    @staticmethod
    def validate_price(price: float, name: str = "Precio") -> float:
        """Valida que el precio sea un número positivo."""
        try:
            price = float(price)
        except (ValueError, TypeError):
            raise ValidationError(f"{name} debe ser un número válido.")
        if price < 0:
            raise ValidationError(f"{name} no puede ser negativo.")
        if price > 999999.99:
            raise ValidationError(f"{name} excede el límite máximo permitido.")
        return round(price, 2)

    @staticmethod
    def validate_stock(stock: int, name: str = "Stock") -> int:
        """Valida que el stock sea un entero no negativo."""
        try:
            stock = int(stock)
        except (ValueError, TypeError):
            raise ValidationError(f"{name} debe ser un número entero.")
        if stock < 0:
            raise ValidationError(f"{name} no puede ser negativo.")
        if stock > 999999:
            raise ValidationError(f"{name} excede el límite máximo.")
        return stock

    @staticmethod
    def validate_product_type(product_type: str) -> str:
        """Valida el tipo de producto."""
        if product_type not in ('FISICO', 'SERVICIO'):
            raise ValidationError("Tipo de producto debe ser 'FISICO' o 'SERVICIO'.")
        return product_type

    @staticmethod
    def validate_margin(cost: float, price: float) -> tuple:
        """Valida que el margen sea coherente."""
        cost = ProductValidator.validate_price(cost, "Costo")
        price = ProductValidator.validate_price(price, "Precio")

        if price < cost and price > 0:
            raise ValidationError("Precio de venta no puede ser menor que el costo.")

        return cost, price

    @staticmethod
    def validate_product_data(sku: str, name: str, tipo: str, costo: float, precio: float,
                              stock: int, stock_min: int) -> dict:
        """Valida todos los datos de un producto en una sola llamada."""
        return {
            'sku': ProductValidator.validate_sku(sku),
            'nombre': ProductValidator.validate_name(name),
            'tipo': ProductValidator.validate_product_type(tipo),
            'costo': ProductValidator.validate_price(costo, "Costo"),
            'precio': ProductValidator.validate_price(precio, "Precio"),
            'stock_actual': ProductValidator.validate_stock(stock, "Stock"),
            'stock_minimo': ProductValidator.validate_stock(stock_min, "Stock Mínimo"),
        }


class SaleValidator:
    """Valida datos de ventas."""

    @staticmethod
    def validate_payment_method(method: str) -> str:
        """Valida el método de pago."""
        valid_methods = ('EFECTIVO', 'TARJETA', 'TRANSFERENCIA')
        if method not in valid_methods:
            raise ValidationError(f"Método de pago debe ser uno de: {', '.join(valid_methods)}")
        return method

    @staticmethod
    def validate_discount(discount: float, subtotal: float) -> float:
        """Valida que el descuento sea válido."""
        try:
            discount = float(discount)
        except (ValueError, TypeError):
            raise ValidationError("Descuento debe ser un número válido.")

        if discount < 0:
            raise ValidationError("El descuento no puede ser negativo.")
        if discount > subtotal:
            raise ValidationError("El descuento no puede ser mayor que el subtotal.")

        return round(discount, 2)

    @staticmethod
    def validate_quantity(quantity: int) -> int:
        """Valida la cantidad de items."""
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            raise ValidationError("Cantidad debe ser un número entero.")

        if quantity <= 0:
            raise ValidationError("Cantidad debe ser mayor que 0.")
        if quantity > 999999:
            raise ValidationError("Cantidad excede el límite permitido.")

        return quantity


class CashRegisterValidator:
    """Valida datos de caja."""

    @staticmethod
    def validate_cash_amount(amount: float) -> float:
        """Valida el monto en efectivo."""
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            raise ValidationError("Monto debe ser un número válido.")

        if amount < 0:
            raise ValidationError("El monto no puede ser negativo.")

        return round(amount, 2)

    @staticmethod
    def validate_initial_fund(amount: float) -> float:
        """Valida el fondo inicial de caja."""
        amount = CashRegisterValidator.validate_cash_amount(amount)
        if amount > 999999.99:
            raise ValidationError("El fondo inicial excede el límite permitido.")
        return amount


class CustomerValidator:
    """Valida datos de clientes."""

    @staticmethod
    def validate_name(name: str) -> str:
        if not name or not isinstance(name, str):
            raise ValidationError("Nombre del cliente no puede estar vacío.")
        name = name.strip()
        if len(name) < 2:
            raise ValidationError("Nombre del cliente debe tener al menos 2 caracteres.")
        if len(name) > 150:
            raise ValidationError("Nombre del cliente excede el máximo permitido.")
        return name

    @staticmethod
    def validate_phone(phone: str) -> str:
        if phone is None or phone == "":
            return ""
        phone = str(phone).strip()
        if len(phone) > 30:
            raise ValidationError("Teléfono excede el máximo permitido.")
        return phone

    @staticmethod
    def validate_email(email: str) -> str:
        if email is None or email == "":
            return ""
        email = str(email).strip()
        if len(email) > 100:
            raise ValidationError("Correo excede el máximo permitido.")
        if "@" not in email:
            raise ValidationError("Correo electrónico no válido.")
        return email

    @staticmethod
    def validate_customer_data(nombre: str, telefono: str = "", correo: str = "",
                              direccion: str = "", ciudad: str = "", notas: str = "") -> dict:
        return {
            'nombre': CustomerValidator.validate_name(nombre),
            'telefono': CustomerValidator.validate_phone(telefono),
            'correo': CustomerValidator.validate_email(correo),
            'direccion': (direccion or '').strip()[:200],
            'ciudad': (ciudad or '').strip()[:100],
            'notas': (notas or '').strip()[:500],
        }


class OrderValidator:
    """Valida datos de pedidos y agenda."""

    VALID_STATUS = (
        'PENDIENTE',
        'CONFIRMADO',
        'EN_PREPARACION',
        'POR_ENTREGAR',
        'EN_INSTALACION',
        'COMPLETADO',
        'CANCELADO'
    )

    VALID_DELIVERY_TYPES = ('ENVIO', 'INSTALACION', 'RECOGIDA', 'LOCAL')

    @staticmethod
    def validate_status(status: str) -> str:
        status = (status or '').strip().upper()
        if status not in OrderValidator.VALID_STATUS:
            raise ValidationError(
                f"Estado del pedido no válido. Opciones: {', '.join(OrderValidator.VALID_STATUS)}"
            )
        return status

    @staticmethod
    def validate_delivery_type(delivery_type: str) -> str:
        delivery_type = (delivery_type or '').strip().upper()
        if delivery_type not in OrderValidator.VALID_DELIVERY_TYPES:
            raise ValidationError(
                f"Tipo de entrega no válido. Opciones: {', '.join(OrderValidator.VALID_DELIVERY_TYPES)}"
            )
        return delivery_type

    @staticmethod
    def validate_money(value, field_name: str = "Monto") -> float:
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} debe ser un número válido.")
        if value < 0:
            raise ValidationError(f"{field_name} no puede ser negativo.")
        return round(value, 2)

    @staticmethod
    def validate_item(item: dict) -> dict:
        if not isinstance(item, dict):
            raise ValidationError("Cada item del pedido debe ser un diccionario.")

        quantity = int(item.get('cantidad', 0))
        if quantity <= 0:
            raise ValidationError("La cantidad del producto debe ser mayor que 0.")

        price = OrderValidator.validate_money(item.get('precio_unitario', 0), "Precio unitario")
        cost = OrderValidator.validate_money(item.get('costo_unitario', 0), "Costo unitario")
        subtotal = round(quantity * price, 2)

        validated_item = {
            'producto_id': item.get('producto_id'),
            'nombre': (item.get('nombre') or 'Producto').strip()[:150],
            'descripcion': (item.get('descripcion') or '').strip()[:300],
            'cantidad': quantity,
            'precio_unitario': price,
            'costo_unitario': cost,
            'subtotal': subtotal,
        }
        return validated_item

    @staticmethod
    def validate_order_data(cliente_id: int, items: list, tipo_entrega: str,
                            descuento: float = 0.0, envio: float = 0.0,
                            anticipo: float = 0.0, notas: str = "") -> dict:
        if not cliente_id:
            raise ValidationError("Debe indicar un cliente válido para el pedido.")
        if not items or len(items) == 0:
            raise ValidationError("Debe incluir al menos un producto o servicio en el pedido.")

        subtotal = 0.0
        for item in items:
            validated_item = OrderValidator.validate_item(item)
            subtotal += validated_item['subtotal']

        subtotal = round(subtotal, 2)
        descuento = OrderValidator.validate_money(descuento, "Descuento")
        envio = OrderValidator.validate_money(envio, "Costo de envío")
        anticipo = OrderValidator.validate_money(anticipo, "Anticipo")

        total = round(subtotal - descuento + envio, 2)
        saldo = round(total - anticipo, 2)

        return {
            'cliente_id': int(cliente_id),
            'tipo_entrega': OrderValidator.validate_delivery_type(tipo_entrega),
            'subtotal': subtotal,
            'descuento': descuento,
            'envio': envio,
            'total': total,
            'anticipo': anticipo,
            'saldo_pendiente': saldo,
            'notas': (notas or '').strip()[:500],
        }


class AgendaValidator:
    """Valida datos de agenda."""

    @staticmethod
    def validate_agenda_status(status: str) -> str:
        valid_status = ('PENDIENTE', 'PROGRAMADA', 'COMPLETADA', 'CANCELADA')
        status = (status or '').strip().upper()
        if status not in valid_status:
            raise ValidationError(f"Estado de agenda no válido. Opciones: {', '.join(valid_status)}")
        return status

    @staticmethod
    def validate_type(item_type: str) -> str:
        valid_types = ('INSTALACION', 'ENTREGA', 'RECOGIDA', 'OTRO')
        item_type = (item_type or '').strip().upper()
        if item_type not in valid_types:
            raise ValidationError(f"Tipo de agenda no válido. Opciones: {', '.join(valid_types)}")
        return item_type

    @staticmethod
    def validate_notes(notes: str) -> str:
        return (notes or '').strip()[:500]

    @staticmethod
    def validate_address(address: str) -> str:
        return (address or '').strip()[:300]

    @staticmethod
    def validate_datetime(value):
        if value is None:
            raise ValidationError("La fecha programada es requerida.")
        return value

    @staticmethod
    def validate_agenda_data(pedido_id: int, fecha_programada, tipo: str, direccion: str = "",
                             observaciones: str = "", estado: str = "PENDIENTE") -> dict:
        if not pedido_id:
            raise ValidationError("Debe indicar un pedido válido para programar la cita.")
        return {
            'pedido_id': int(pedido_id),
            'fecha_programada': AgendaValidator.validate_datetime(fecha_programada),
            'tipo': AgendaValidator.validate_type(tipo),
            'direccion': AgendaValidator.validate_address(direccion),
            'observaciones': AgendaValidator.validate_notes(observaciones),
            'estado': AgendaValidator.validate_agenda_status(estado),
        }


__all__ = [
    'ValidationError',
    'ProductValidator',
    'SaleValidator',
    'CashRegisterValidator',
    'CustomerValidator',
    'OrderValidator',
    'AgendaValidator',
]
