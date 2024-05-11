import asyncio
import websockets
import json

class WebSocketServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = set()
        self.client_states = {}  # 클라이언트의 상태를 저장할 딕셔너리
        self.on = True
        self.time = 30
        self.turn = [1]

    async def register(self, websocket):
        self.clients.add(websocket)
        self.client_states[websocket] = 0  # 초기 상태를 0으로 설정
        print(f"Client {websocket.remote_address} connected with initial state 0.")

    async def unregister(self, websocket):
        self.clients.remove(websocket)
        del self.client_states[websocket]  # 클라이언트의 상태 정보도 삭제
        print(f"Client {websocket.remote_address} disconnected.")

    async def handle_client(self, websocket, path):
        await self.register(websocket)
        try:
            # 동시에 메시지 읽기 및 쓰기 루프를 실행
            reader_task = asyncio.create_task(self.read_messages(websocket))
            writer_task = asyncio.create_task(self.write_messages(websocket))
            done, pending = await asyncio.wait(
                [reader_task, writer_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
        finally:
            await self.unregister(websocket)

    async def read_messages(self, websocket):
        try:
            async for message in websocket:
                data = json.loads(message)
                print(f"Received from {websocket.remote_address}: {data}")
                
                if self.client_states[websocket] == 42:
                    # 1,2,3,4 - 30s 시작
                    # 101,102,103,104 - 45s 시작
                    # 200 - 60s 멀리건
                    if data in range(1, 5):
                        self.time = 30
                        self.turn = [data]
                    if data in range(101, 105):
                        self.time = 45
                        self.turn = [data - 100]
                    if data == 200:
                        self.time = 90
                        self.turn = [1, 2, 3, 4]
                elif data == 42:
                    self.client_states[websocket] = 42
                    print(f"Updated state for {websocket.remote_address}: admin(42)")
                elif data in range(1, 5):
                    self.client_states[websocket] = int(data)
                    print(f"Updated state for {websocket.remote_address}: {self.client_states[websocket]}")
                elif data == 99 and self.client_states[websocket] in self.turn and len(self.turn) == 1: # 99 means turn end
                    self.time = 30
                    self.turn[0] += self.turn[0]
                    if self.turn[0] == 5:
                        self.turn[0] = 1
                    print(f"Turn changed to {self.turn}")
        except asyncio.CancelledError:
            print("Read loop was cancelled")

    async def write_messages(self, websocket):
        try:
            while True:
                # 여기서 메시지 생성 또는 스케줄링 가능
                isTurn = (self.client_states[websocket] in self.turn) and self.on
                message = {
                    "time": self.time,
                    "is_turn": isTurn
                }
                await websocket.send(json.dumps(message))
                print(f"Sent to {websocket.remote_address}: {message}")
                await asyncio.sleep(1)
                if (isTurn and self.time > 0):
                    self.time -= 1
        except asyncio.CancelledError:
            print("Write loop was cancelled")

    async def run(self):
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"Server started at ws://{self.host}:{self.port}")
            await asyncio.Future()  # 서버가 영구적으로 실행되게 함

async def main():
    server = WebSocketServer('192.168.0.50', 5001)
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
