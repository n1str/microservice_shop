import os
import asyncio
import logging
from concurrent import futures
import grpc
from termcolor import colored

import main_pb2
import main_pb2_grpc
import order_pb2
import order_pb2_grpc
import user_pb2
import user_pb2_grpc

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(os.getenv('SERVICE_NAME', 'MAIN_SERVICE'))

class MainService(main_pb2_grpc.MainServiceServicer):
    def __init__(self):
        self.user_channel = grpc.aio.insecure_channel('user_service:50051')
        self.user_stub = user_pb2_grpc.UserServiceStub(self.user_channel)
        
        self.order_channel = grpc.aio.insecure_channel('order_service:50052')
        self.order_stub = order_pb2_grpc.OrderServiceStub(self.order_channel)

    async def ProcessOrder(self, request, context):
        try:
            logger.info(colored(f"Processing order for user: {request.user_id}", "cyan"))
            
            try:
                user_response = await self.user_stub.GetUser(
                    user_pb2.GetUserRequest(user_id=request.user_id)
                )
                if not user_response or not user_response.user_id:
                    logger.warning(colored(f"User not found: {request.user_id}", "yellow"))
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details('User not found')
                    return main_pb2.ProcessOrderResponse()
            except grpc.RpcError as e:
                logger.error(colored(f"Error verifying user: {str(e)}", "red"))
                context.set_code(e.code())
                context.set_details(e.details())
                return main_pb2.ProcessOrderResponse()

            try:
                order_items = [
                    order_pb2.OrderItem(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        price=item.price
                    ) for item in request.items
                ]
                
                order_response = await self.order_stub.CreateOrder(
                    order_pb2.CreateOrderRequest(
                        user_id=request.user_id,
                        items=order_items
                    )
                )
                
                logger.info(colored(f"Order created successfully: {order_response.order_id}", "green"))
                
                return main_pb2.ProcessOrderResponse(
                    order_id=order_response.order_id,
                    status=order_response.status,
                    message="Order processed successfully"
                )
            except grpc.RpcError as e:
                logger.error(colored(f"Error creating order: {str(e)}", "red"))
                context.set_code(e.code())
                context.set_details(e.details())
                return main_pb2.ProcessOrderResponse()

        except Exception as e:
            logger.error(colored(f"Error processing order: {str(e)}", "red"))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal error occurred')
            return main_pb2.ProcessOrderResponse()

    async def GetOrderStatus(self, request, context):
        try:
            logger.info(colored(f"Getting order status for order: {request.order_id}", "cyan"))
            
            try:
                order_response = await self.order_stub.GetOrder(
                    order_pb2.GetOrderRequest(order_id=request.order_id)
                )
                
                if not order_response or not order_response.order_id:
                    logger.warning(colored(f"Order not found: {request.order_id}", "yellow"))
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details('Order not found')
                    return main_pb2.GetOrderStatusResponse()
                
                items = [
                    main_pb2.OrderItem(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        price=item.price
                    ) for item in order_response.items
                ]
                
                return main_pb2.GetOrderStatusResponse(
                    order_id=order_response.order_id,
                    status=order_response.status,
                    items=items,
                    total_amount=order_response.total_amount,
                    created_at=order_response.created_at
                )
            
            except grpc.RpcError as e:
                logger.error(colored(f"Error getting order status: {str(e)}", "red"))
                context.set_code(e.code())
                context.set_details(e.details())
                return main_pb2.GetOrderStatusResponse()

        except Exception as e:
            logger.error(colored(f"Error getting order status: {str(e)}", "red"))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal error occurred')
            return main_pb2.GetOrderStatusResponse()

async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    main_pb2_grpc.add_MainServiceServicer_to_server(MainService(), server)
    listen_addr = '[::]:50050'
    server.add_insecure_port(listen_addr)
    logger.info(colored(f"Starting server on {listen_addr}", "green"))
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    logger.info(colored("Main service starting...", "green"))
    asyncio.run(serve())
