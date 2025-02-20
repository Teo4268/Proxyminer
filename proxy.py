import asyncio
import uvloop
import websockets
import json

# Cấu hình proxy cho Zpool
POOL_URL = "wss://power2b.na.mine.zpool.ca:6242"  # Pool Zpool thuật toán Power2b
PROXY_HOST = "0.0.0.0"  # Lắng nghe tất cả kết nối
PROXY_PORT = 8000 # Cổng proxy hoạt động
NEW_WORKER_NAME = "ProxyMiner"  # Tên worker khi gửi đến pool

current_job = None  # Công việc hiện tại từ pool
miners = set()  # Danh sách miners kết nối

async def fetch_job_from_pool():
    """Nhận công việc từ Zpool và gửi cho tất cả miners"""
    global current_job
    async with websockets.connect(POOL_URL) as pool_ws:
        print("✅ Kết nối với Zpool thành công!")

        async for message in pool_ws:
            data = json.loads(message)

            if "method" in data and data["method"] == "mining.notify":
                current_job = message  # Lưu công việc mới
                print("🆕 Nhận job mới từ pool, cập nhật cho miners...")

                # Gửi job mới cho tất cả miners
                for miner in miners:
                    await miner.send(current_job)

async def handle_miner(websocket, path):
    """Xử lý miners kết nối đến proxy"""
    miners.add(websocket)

    # Gửi công việc hiện tại cho miner khi kết nối
    if current_job:
        await websocket.send(current_job)

    try:
        async for message in websocket:
            data = json.loads(message)

            # Nếu miner gửi yêu cầu "mining.authorize", đổi tên worker
            if "method" in data and data["method"] == "mining.authorize":
                data["params"][0] = NEW_WORKER_NAME  # Thay đổi tên worker

            # Nếu miner gửi share, gửi lên Zpool
            async with websockets.connect(POOL_URL) as pool_ws:
                await pool_ws.send(json.dumps(data))

    except:
        miners.remove(websocket)  # Xóa miner nếu mất kết nối

async def main():
    """Khởi chạy proxy"""
    asyncio.create_task(fetch_job_from_pool())  # Nhận job từ pool
    async with websockets.serve(handle_miner, PROXY_HOST, PROXY_PORT):
        print(f"🚀 Proxy chạy trên {PROXY_HOST}:{PROXY_PORT}, hỗ trợ 100 miners!")
        await asyncio.Future()  # Giữ chương trình chạy

if __name__ == "__main__":
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # Dùng uvloop tăng tốc
    asyncio.run(main())
