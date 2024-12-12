import os
import asyncio
import logging
from concurrent import futures
import grpc
from termcolor import colored
import motor.motor_asyncio
from datetime import datetime
from order_pb2 import (
    CreateOrderRequest,
    OrderResponse,
    GetOrderRequest,
    UpdateOrderStatusRequest,
    OrderItem
)
import order_pb2_grpc

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(os.getenv('SERVICE_NAME', 'ORDER_SERVICE'))

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB = os.getenv('MONGODB_DB', 'orderdb')

client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = client[MONGODB_DB]
orders_collection = db.orders

class OrderService(order_pb2_grpc.OrderServiceServicer):
    async def CreateOrder(self, request, context):
        try:
            logger.info(colored(f"Creating order for user: {request.user_id}", "cyan"))
            
            items = [{
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price
            } for item in request.items]
            
            total_amount = sum(item.price * item.quantity for item in request.items)
            
            order_doc = {
                "user_id": request.user_id,
                "items": items,
                "status": "PENDING",
                "total_amount": total_amount,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = await orders_collection.insert_one(order_doc)
            order_id = str(result.inserted_id)
            
            logger.info(colored(f"Order created successfully with ID: {order_id}", "green"))
            
            return OrderResponse(
                order_id=order_id,
                user_id=request.user_id,
                items=[OrderItem(
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    price=item["price"]
                ) for item in items],
                status="PENDING",
                total_amount=total_amount,
                created_at=order_doc["created_at"]
            )
        except Exception as e:
            logger.error(colored(f"Error creating order: {str(e)}", "red"))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal error occurred')
            return OrderResponse()

    async def GetOrder(self, request, context):
        try:
            logger.info(colored(f"Getting order with ID: {request.order_id}", "cyan"))
            
            from bson import ObjectId
            order = await orders_collection.find_one({"_id": ObjectId(request.order_id)})
            
            if order:
                logger.info(colored(f"Order found: {order['_id']}", "green"))
                return OrderResponse(
                    order_id=str(order['_id']),
                    user_id=order['user_id'],
                    items=[OrderItem(
                        product_id=item['product_id'],
                        quantity=item['quantity'],
                        price=item['price']
                    ) for item in order['items']],
                    status=order['status'],
                    total_amount=order['total_amount'],
                    created_at=order['created_at']
                )
            else:
                logger.warning(colored(f"Order not found with ID: {request.order_id}", "yellow"))
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details('Order not found')
                return OrderResponse()
        except Exception as e:
            logger.error(colored(f"Error getting order: {str(e)}", "red"))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal error occurred')
            return OrderResponse()

    async def UpdateOrderStatus(self, request, context):
        try:
            logger.info(colored(f"Updating order status: {request.order_id} to {request.status}", "cyan"))
            
            from bson import ObjectId
            result = await orders_collection.update_one(
                {"_id": ObjectId(request.order_id)},
                {"$set": {"status": request.status}}
            )
            
            if result.modified_count == 0:
                logger.warning(colored(f"Order not found with ID: {request.order_id}", "yellow"))
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details('Order not found')
                return OrderResponse()
            
            order = await orders_collection.find_one({"_id": ObjectId(request.order_id)})
            
            logger.info(colored(f"Order status updated successfully: {request.order_id}", "green"))
            
            return OrderResponse(
                order_id=str(order['_id']),
                user_id=order['user_id'],
                items=[OrderItem(
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    price=item['price']
                ) for item in order['items']],
                status=order['status'],
                total_amount=order['total_amount'],
                created_at=order['created_at']
            )
        except Exception as e:
            logger.error(colored(f"Error updating order status: {str(e)}", "red"))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal error occurred')
            return OrderResponse()

async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    order_pb2_grpc.add_OrderServiceServicer_to_server(OrderService(), server)
    listen_addr = '[::]:50052'
    server.add_insecure_port(listen_addr)
    logger.info(colored(f"Starting server on {listen_addr}", "green"))
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    logger.info(colored("Order service starting...", "green"))
    asyncio.run(serve())