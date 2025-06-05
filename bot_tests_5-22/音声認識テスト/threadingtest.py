import threading
import time

def threading_function():
    print("スレッド開始")
    time.sleep(20)  # 20秒間待機
    print("スレッド終了")

# スレッドのインスタンスを作成
thread_instance = threading.Thread(target=threading_function)
thread_instance.start()

# スレッドの状態を確認
print(f"スレッド開始直後の状態: {thread_instance.is_alive()}")

# 10秒だけ待機
thread_instance.join(timeout=10)

# タイムアウト後のスレッド状態を確認
print(f"10秒待機後のスレッド状態: {thread_instance.is_alive()}")

# メインスレッドの処理
print("メインスレッドは続行")

# 最終的にスレッドが完全に終了するまで待機
thread_instance.join()  # 20秒後に終了
print("全スレッド終了")