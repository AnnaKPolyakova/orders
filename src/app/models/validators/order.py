from datetime import datetime

from pydantic import BaseModel, Field

from src.app.models.db_models.order import PaymentStatus


class OrderItemCreate(BaseModel):
    """Schema for creating order item inside order"""

    product_id: int = Field(..., description="ID of product")
    quantity: int = Field(1, ge=1, description="Quantity of product in order")


class OrderItemRead(BaseModel):
    """Schema for reading order item"""

    id: int
    order_id: int
    product_id: int
    quantity: int
    price: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderRead(BaseModel):
    """Schema for reading order"""

    id: int
    user_id: int
    payment_status: PaymentStatus
    items: list[OrderItemRead]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    """Schema for creating order"""

    items: list[OrderItemCreate] = Field(
        ..., min_length=1, description="List of items in order"
    )


class OrderItemUpdate(BaseModel):
    """Schema for updating existing order item"""

    item_id: int = Field(..., description="ID of order item to update")
    quantity: int = Field(
        1, ge=1, description="New quantity for product in order"
    )


class OrderUpdate(BaseModel):
    """Schema for updating order"""

    delete_item_ids: list[int] | None = Field(
        None,
        description="List of order item IDs to remove from order",
    )
    new_items: list[OrderItemCreate] | None = Field(
        None,
        description="List of new items to add to order",
    )
    update_items: list[OrderItemUpdate] | None = Field(
        None,
        description="List of existing items to update (by item_id)",
    )


class OrderPaymentUpdate(BaseModel):
    """Schema for updating payment status"""

    payment_status: PaymentStatus = Field(
        ..., description="New payment status for order"
    )
