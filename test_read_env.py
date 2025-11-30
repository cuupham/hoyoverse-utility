import os

def main():
    # Lấy secret từ env (GitHub Actions inject vào)
    cookie = os.getenv("HOYOVERSE_COOKIE")
    
    if cookie:
        print("Cookie đã load thành công!")
        # Không in nguyên cookie ra log nếu là secret thật
        # Nếu muốn test, có thể in 1 phần nhỏ
        print("First 50 chars:", cookie[:50])
    else:
        print("Chưa có cookie trong env")


    cookie = os.getenv("Path")
    
    if cookie:
        print("Cookie đã load thành công!")
        # Không in nguyên cookie ra log nếu là secret thật
        # Nếu muốn test, có thể in 1 phần nhỏ
        print("First 50 chars:", cookie[:50])
    else:
if __name__ == "__main__":
    main()
