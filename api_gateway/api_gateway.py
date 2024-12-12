from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import grpc
import user_pb2
import user_pb2_grpc
import order_pb2
import order_pb2_grpc
import main_pb2
import main_pb2_grpc
from typing import Optional
import uvicorn

app = FastAPI(title="Microservices API Gateway")

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class OrderItem(BaseModel):
    product_id: str
    quantity: int
    price: float

class CreateOrder(BaseModel):
    user_id: str
    items: List[OrderItem]

def get_user_client():
    channel = grpc.insecure_channel('user_service:50051')
    return user_pb2_grpc.UserServiceStub(channel)

def get_order_client():
    channel = grpc.insecure_channel('order_service:50052')
    return order_pb2_grpc.OrderServiceStub(channel)

def get_main_client():
    channel = grpc.insecure_channel('main_service:50050')
    return main_pb2_grpc.MainServiceStub(channel)


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Microservices API"}

@app.post("/users")
async def create_user(user: UserCreate):
    try:
        client = get_user_client()
        response = client.CreateUser(
            user_pb2.CreateUserRequest(
                username=user.username,
                email=user.email,
                password=user.password
            )
        )
        return {
            "user_id": response.user_id,
            "username": response.username,
            "email": response.email
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/login")
async def login_user(user: UserLogin):
    try:
        client = get_user_client()
        response = client.AuthenticateUser(
            user_pb2.AuthRequest(
                username=user.username,
                password=user.password
            )
        )
        return {"token": response.token}
    except grpc.RpcError as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    try:
        client = get_user_client()
        response = client.GetUser(user_pb2.GetUserRequest(user_id=user_id))
        return {
            "user_id": response.user_id,
            "username": response.username,
            "email": response.email
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/orders")
async def create_order(order: CreateOrder):
    try:
        client = get_main_client()
        items = [
            main_pb2.OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price
            ) for item in order.items
        ]
        
        response = client.ProcessOrder(
            main_pb2.ProcessOrderRequest(
                user_id=order.user_id,
                items=items
            )
        )
        
        return {
            "order_id": response.order_id,
            "status": response.status,
            "message": response.message
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    try:
        client = get_main_client()
        response = client.GetOrderStatus(
            main_pb2.GetOrderStatusRequest(order_id=order_id)
        )
        return {
            "order_id": response.order_id,
            "status": response.status,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price": item.price
                } for item in response.items
            ],
            "total_amount": response.total_amount,
            "created_at": response.created_at
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=404, detail="Order not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)